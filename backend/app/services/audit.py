"""
Audit Logging Service
Records security and meaningful schedule actions with user scoping,
sanitized metadata, IP address, and user agent.
"""
import json
import logging
from typing import Any, Optional
from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def record_audit_log(
    db: Session,
    user_id: int,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    description: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> Optional[AuditLog]:
    """
    Records an audit log entry in the database.
    Catches exceptions so audit logging failures never break primary user operations.
    """
    try:
        ip_address = None
        user_agent = None

        if request is not None:
            # Client IP: check X-Forwarded-For first, then client host
            x_forwarded = request.headers.get("x-forwarded-for")
            if x_forwarded:
                ip_address = x_forwarded.split(",")[0].strip()[:45]
            elif request.client and request.client.host:
                ip_address = request.client.host[:45]

            ua = request.headers.get("user-agent")
            if ua:
                user_agent = ua[:255]

        # Sanitize metadata: remove passwords, tokens, secrets
        clean_meta = None
        if metadata:
            sanitized = {}
            for k, v in metadata.items():
                lower_k = str(k).lower()
                if any(sec in lower_k for sec in ("password", "token", "secret", "api_key", "credentials")):
                    sanitized[k] = "[REDACTED]"
                else:
                    sanitized[k] = v
            try:
                clean_meta = json.dumps(sanitized)
            except Exception:
                clean_meta = str(sanitized)

        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            metadata_json=clean_meta,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    except Exception as exc:
        logger.warning(f"Failed to record audit log ({action} for user {user_id}): {exc}")
        try:
            db.rollback()
        except Exception:
            pass
        return None
