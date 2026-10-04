"""Trusted, configured delivery for password recovery links."""
import smtplib
from email.message import EmailMessage

from app.config import settings


def delivery_available() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_FROM and settings.SMTP_USER and settings.SMTP_PASS and settings.PASSWORD_RESET_PUBLIC_URL)


def send_reset_link(address: str, token: str) -> None:
    if not delivery_available():
        raise RuntimeError("Password recovery SMTP is not configured")
    # The frontend accepts the token from the link; never put it in a log or API response.
    origin = settings.PASSWORD_RESET_PUBLIC_URL.rstrip("/")
    message = EmailMessage()
    message["Subject"] = "SyncShift password recovery"
    message["From"] = settings.SMTP_FROM
    message["To"] = address
    message.set_content(f"Open {origin}/login?reset_token={token} to set your password. This link expires in 30 minutes. If you did not request it, ignore this email.")
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASS)
        server.send_message(message)
