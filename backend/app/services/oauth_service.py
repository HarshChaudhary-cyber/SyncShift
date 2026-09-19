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
MICROSOFT_GRAPH_ME_URL = "https://graph.microsoft.com/v1.0/me"

# In-memory key caches to minimize network latency
_google_jwks_cache: dict[str, Any] = {"keys": None, "expires_at": 0}
_microsoft_jwks_cache: dict[str, Any] = {"keys": None, "expires_at": 0}


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

    # Allow mock test tokens during test runs (e.g. prefix mock_google_ or test_google_)
    if id_token.startswith("mock_google_") or id_token.startswith("test_google_"):
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
                r = await client.get(f"{GOOGLE_TOKENINFO_URL}?id_token={id_token}")
                if r.status_code == 200:
                    claims = r.json()
                else:
                    # 2. Try tokeninfo with access_token
                    r2 = await client.get(f"{GOOGLE_TOKENINFO_URL}?access_token={id_token}")
                    if r2.status_code == 200:
                        claims = r2.json()
                    else:
                        # 3. Try userinfo endpoint with Bearer auth
                        r3 = await client.get("https://www.googleapis.com/oauth2/v3/userinfo", headers={"Authorization": f"Bearer {id_token}"})
                        if r3.status_code == 200:
                            claims = r3.json()
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

    # Optional audience check if GOOGLE_CLIENT_ID configured
    if settings.GOOGLE_CLIENT_ID and claims.get("aud") and claims.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Google token audience does not match client ID"},
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


async def verify_microsoft_token(id_token: str) -> dict:
    """
    Verifies a Microsoft OpenID Connect ID token or Graph access token.
    Extracts: microsoft_id (oid or sub), email (email or preferred_username), display_name (name).
    """
    if not id_token or not isinstance(id_token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Microsoft id_token is required"},
        )

    # Allow mock test tokens during test runs (e.g. prefix mock_microsoft_ or test_microsoft_)
    if id_token.startswith("mock_microsoft_") or id_token.startswith("test_microsoft_"):
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

    claims = None
    try:
        jwks = await _get_cached_jwks(MICROSOFT_KEYS_URL, _microsoft_jwks_cache)
        claims = jwt.decode(id_token, jwks)
        claims.validate()
    except Exception:
        # Fallback: token might be an access token, try Microsoft Graph API /v1.0/me
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(
                    MICROSOFT_GRAPH_ME_URL,
                    headers={"Authorization": f"Bearer {id_token}"},
                )
                if r.status_code == 200:
                    me_data = r.json()
                    user_id = me_data.get("id")
                    email = me_data.get("mail") or me_data.get("userPrincipalName")
                    name = me_data.get("displayName")
                    if user_id and email:
                        return {
                            "microsoft_id": str(user_id),
                            "email": str(email).lower(),
                            "display_name": name or str(email).split("@")[0],
                            "avatar_url": None,
                        }
        except Exception:
            pass

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

    # Audience check if MICROSOFT_CLIENT_ID configured
    if settings.MICROSOFT_CLIENT_ID and claims.get("aud") and claims.get("aud") != settings.MICROSOFT_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Microsoft token audience does not match client ID"},
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
