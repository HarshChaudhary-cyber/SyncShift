"""Operator-only bootstrap. Never called by a public API; does not create passwords."""
import argparse
from app.database import SessionLocal
from app.models import User, Institution, InstitutionMembership
from app.services.academic_access import history


def main():
    parser = argparse.ArgumentParser(description="Grant the first super admin to an existing university and account")
    parser.add_argument("--email", required=True)
    parser.add_argument("--institution-code", required=True)
    parser.add_argument("--institution-name", help="Create this university if the code does not exist")
    args = parser.parse_args()
    with SessionLocal() as db:
        user = db.query(User).filter_by(email=args.email.lower(), deleted_at=None).first()
        if not user:
            parser.error("Register the intended account first, then verify its owner out of band")
        institution = db.query(Institution).filter_by(code=args.institution_code.upper(), deleted_at=None).first()
        if not institution:
            if not args.institution_name:
                parser.error("University does not exist; supply --institution-name to create it")
            institution = Institution(name=args.institution_name, code=args.institution_code.upper(), is_active=True)
            db.add(institution); db.flush()
        if db.query(InstitutionMembership).filter_by(institution_id=institution.id, role="super_admin", status="active", deleted_at=None).first():
            parser.error("Initial setup already completed. Use protected administration for subsequent role changes")
        m = db.query(InstitutionMembership).filter_by(user_id=user.id, institution_id=institution.id).first()
        if not m:
            m = InstitutionMembership(user_id=user.id, institution_id=institution.id)
            db.add(m)
        m.role, m.status, m.deleted_at = "super_admin", "active", None
        history(db, user.id, "super_admin_bootstrapped", f"Operator provisioned user {user.id}", institution_id=institution.id)
        db.commit()
        print("Initial university super admin configured. Sign in again to refresh your role.")


if __name__ == "__main__":
    main()
