"""Operator-only password setup after identity verification outside SyncShift."""
import argparse
import getpass

from app.config import settings
from app.database import SessionLocal
from app.models.user import User
from app.routers.auth import hash_password, validate_password_strength


def main() -> None:
    parser = argparse.ArgumentParser(description="Set a verified account password from a trusted local shell")
    parser.add_argument("--email", required=True)
    parser.add_argument("--identity-verified", action="store_true", required=True,
                        help="Confirm the account owner was verified out of band")
    args = parser.parse_args()
    if settings.ENV.lower() in {"production", "prod", "live"}:
        parser.error("Use configured SMTP recovery in production")
    first = getpass.getpass("New password: ")
    if first != getpass.getpass("Repeat new password: "):
        parser.error("Passwords do not match")
    validate_password_strength(first)
    with SessionLocal() as db:
        user = db.query(User).filter_by(email=args.email.strip().lower(), deleted_at=None).first()
        if not user:
            parser.error("Account not found")
        user.password_hash = hash_password(first)
        user.password_reset_jti = None
        user.session_version += 1
        db.commit()
    print("Password set. Existing sessions were revoked.")


if __name__ == "__main__":
    main()
