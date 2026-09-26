"""OAuth Verification Service for Google and Microsoft

Handles cryptographic verification of ID tokens,
fetching provider public keys (JWKS), and extracting profile claims.
"""
from typing import Optional, Any
import time
import httpx
from fastapi import HTTPException, status
from authlib.jose import jwt, JsonWebKey
from app.config import settings

GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
MICROSOFT_KEYS_URL = "https://login.microsoftonline.com/common/discovery/v2.0/keys"

# In-memory key caches to minimize network latency
_google_jwks_cache: dict[str, Any] = {"keys": None, "expires_at": 0}
_microsoft_jwks_cache: dict[str, Any] = {"keys": None, "expires_at": 0}


def _allow_test_oauth_tokens() -> bool:
    """Overridden only by the test suite; never enabled by runtime settings."""
    return False


async def _get_cached_jwks(url: str, cache_dict: dict[str, Any]) -> JsonWebKey:
    now = time.time()
    if cache_dict["keys"] and now < cache_dict["expires_at"]:
        return cache_dict["keys"]

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"code": "service_unavailable", "message": f"Failed to fetch public keys from {url}"},
                )
            jwks_data = resp.json()
            jwks = JsonWebKey.import_key_set(jwks_data)
            cache_dict["keys"] = jwks
            # Cache for 1 hour
            cache_dict["expires_at"] = now + 3600
            return jwks
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "service_unavailable", "message": f"Network error contacting identity provider: {str(exc)}"},
        )


async def verify_google_id_token(id_token: str) -> dict:
    """
    Verifies a Google ID token.
    Extracts: google_id (sub), email, name, avatar_url (picture).
    """
    if not id_token or not isinstance(id_token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Google id_token is required"},
        )

    # Synthetic identities are only valid inside the isolated test suite.
    if id_token.startswith("mock_google_") or id_token.startswith("test_google_"):
        if not _allow_test_oauth_tokens():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "invalid_token", "message": "Invalid Google token"},
            )
        parts = id_token.split(":", 4)
        sub = parts[1] if len(parts) > 1 else "mock_google_user_123"
        email = parts[2] if len(parts) > 2 else f"{sub}@gmail.com"
        name = parts[3] if len(parts) > 3 else "Mock Google User"
        picture = parts[4] if len(parts) > 4 else "https://lh3.googleusercontent.com/a/mock"
        return {
            "google_id": sub,
            "email": email.lower(),
            "display_name": name,
            "avatar_url": picture,
        }

    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "service_not_configured", "message": "Google sign-in is not configured"},
        )

    claims = None
    try:
        jwks = await _get_cached_jwks(GOOGLE_CERTS_URL, _google_jwks_cache)
        claims = jwt.decode(id_token, jwks)
        claims.validate()
    except Exception:
        # Fallback to Google's tokeninfo / userinfo endpoints for additional compatibility
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                # 1. Try tokeninfo with id_token
                r = await client.get(GOOGLE_TOKENINFO_URL, params={"id_token": id_token})
                if r.status_code == 200:
                    claims = r.json()
                else:
                    # The browser SDK returns an access token. Verify its
                    # intended client before requesting the user's profile.
                    r2 = await client.get(GOOGLE_TOKENINFO_URL, params={"access_token": id_token})
                    if r2.status_code == 200:
                        token_info = r2.json()
                        token_audience = token_info.get("aud") or token_info.get("issued_to")
                        if token_audience != settings.GOOGLE_CLIENT_ID:
                            raise HTTPException(
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                detail={"code": "invalid_token", "message": "Google token audience does not match client ID"},
                            )
                        r3 = await client.get(
                            "https://www.googleapis.com/oauth2/v3/userinfo",
                            headers={"Authorization": f"Bearer {id_token}"},
                        )
                        if r3.status_code == 200:
                            claims = {**r3.json(), "aud": token_audience, "iss": "https://accounts.google.com"}
                        else:
                            raise HTTPException(
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                detail={"code": "invalid_token", "message": "Invalid or expired Google token"},
                            )
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"code": "invalid_token", "message": "Invalid or expired Google token"},
                        )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "service_unavailable", "message": f"Failed to reach Google token endpoint: {str(exc)}"},
            )

    if not claims or "sub" not in claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Google token missing user identity ('sub')"},
        )

    if claims.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Google token audience does not match client ID"},
        )

    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Google token issuer is invalid"},
        )

    if str(claims.get("email_verified", "")).lower() not in ("true", "1"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Google account email is not verified"},
        )

    email = claims.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "email_missing", "message": "No email address found in Google token"},
        )

    return {
        "google_id": str(claims["sub"]),
        "email": str(email).lower(),
        "display_name": claims.get("name") or str(email).split("@")[0],
        "avatar_url": claims.get("picture"),
    }


async def verify_microsoft_token(id_token: str, expected_nonce: Optional[str] = None) -> dict:
    """
    Verifies a Microsoft OpenID Connect ID token.
    Extracts: microsoft_id (oid or sub), email (email or preferred_username), display_name (name).
    """
    if not id_token or not isinstance(id_token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Microsoft id_token is required"},
        )

    # Synthetic identities are only valid inside the isolated test suite.
    if id_token.startswith("mock_microsoft_") or id_token.startswith("test_microsoft_"):
        if not _allow_test_oauth_tokens():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "invalid_token", "message": "Invalid Microsoft token"},
            )
        parts = id_token.split(":", 3)
        sub = parts[1] if len(parts) > 1 else "mock_microsoft_user_123"
        email = parts[2] if len(parts) > 2 else f"{sub}@outlook.com"
        name = parts[3] if len(parts) > 3 else "Mock Microsoft User"
        return {
            "microsoft_id": sub,
            "email": email.lower(),
            "display_name": name,
            "avatar_url": None,
        }

    if not settings.MICROSOFT_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "service_not_configured", "message": "Microsoft sign-in is not configured"},
        )

    if not expected_nonce:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Microsoft sign-in nonce is required"},
        )

    claims = None
    try:
        jwks = await _get_cached_jwks(MICROSOFT_KEYS_URL, _microsoft_jwks_cache)
        claims = jwt.decode(id_token, jwks)
        claims.validate()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Invalid or expired Microsoft token"},
        )

    # In Microsoft ID tokens, 'oid' is the immutable object ID; 'sub' is pairwise
    microsoft_id = claims.get("oid") or claims.get("sub")
    if not microsoft_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Microsoft token missing user identity ('oid'/'sub')"},
        )

    if claims.get("aud") != settings.MICROSOFT_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Microsoft token audience does not match client ID"},
        )

    tenant_id = claims.get("tid")
    expected_issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0" if tenant_id else None
    if not expected_issuer or claims.get("iss") != expected_issuer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Microsoft token issuer is invalid"},
        )
    tenant_setting = settings.MICROSOFT_TENANT_ID
    if tenant_setting not in ("common", "organizations", "consumers") and tenant_id != tenant_setting:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Microsoft token tenant does not match"},
        )
    if expected_nonce is not None and claims.get("nonce") != expected_nonce:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Microsoft sign-in nonce does not match"},
        )

    email = claims.get("email") or claims.get("preferred_username") or claims.get("upn")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "email_missing", "message": "No email address found in Microsoft token"},
        )

    return {
        "microsoft_id": str(microsoft_id),
        "email": str(email).lower(),
        "display_name": claims.get("name") or str(email).split("@")[0],
        "avatar_url": None,
    }
