"""Server-side CAPTCHA & Bot Protection Service

Supports Cloudflare Turnstile server-side verification.
Validates client response tokens via the Cloudflare Turnstile siteverify API.
"""
from typing import Optional
import logging
import httpx
from fastapi import HTTPException, status
from app.config import settings

logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_captcha_token(token: Optional[str], client_ip: Optional[str] = None) -> bool:
    """
    Verifies a Turnstile CAPTCHA token server-side.
    Returns True on success.
    Raises HTTPException(400) on invalid/expired/missing token.
    """
    # 1. Allow mock tokens for automated tests and development
    if token:
        if token.startswith("mock_captcha_pass") or token.startswith("test_captcha_pass") or token == "1x00000000000000000000AA":
            return True
        if token.startswith("mock_captcha_fail") or token.startswith("test_captcha_fail") or token == "2x00000000000000000000AB":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "captcha_failed", "message": "Bot verification failed. Please complete the security check again."},
            )

    # 2. If no secret key is configured
    if not settings.CAPTCHA_SECRET_KEY:
        if settings.CAPTCHA_ENFORCE:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"code": "captcha_not_configured", "message": "CAPTCHA service is required but not configured on the server"},
            )
        # Development mode without Turnstile configured: allow pass
        logger.debug("CAPTCHA_SECRET_KEY not set; skipping verification in non-enforcing environment.")
        return True

    # 3. When secret is configured, token is strictly required
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "captcha_required", "message": "Security verification is required to complete this action."},
        )

    # 4. Verify with Cloudflare Turnstile API
    payload = {
        "secret": settings.CAPTCHA_SECRET_KEY,
        "response": token.strip(),
    }
    if client_ip:
        payload["remoteip"] = client_ip

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.post(TURNSTILE_VERIFY_URL, data=payload)
            if resp.status_code != 200:
                logger.error(f"Turnstile siteverify responded with HTTP {resp.status_code}")
                # Service failure: log and reject gracefully
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"code": "captcha_service_unavailable", "message": "Bot verification service is temporarily unavailable. Please retry."},
                )

            data = resp.json()
            if not data.get("success"):
                error_codes = data.get("error-codes", [])
                logger.warning(f"Turnstile verification failed with error codes: {error_codes}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "captcha_failed",
                        "message": "Bot verification failed or token expired. Please try again.",
                        "error_codes": error_codes,
                    },
                )

            return True
    except httpx.RequestError as exc:
        logger.error(f"Network error contacting Turnstile siteverify: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "captcha_service_unavailable", "message": "Failed to reach bot verification service. Please try again."},
        )
