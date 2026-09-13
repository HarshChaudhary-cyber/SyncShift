"""
Audit Logs Router
Provides paginated, strictly user-isolated audit log activity for the authenticated user.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogListResponse, AuditLogOut
from app.schemas.common import DataResponse

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=DataResponse[AuditLogListResponse])
def get_user_audit_logs(
    limit: int = Query(20, ge=1, le=100, description="Max logs to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve security and activity audit logs for the authenticated student.
    Strictly scoped to current_user.user_id from JWT token.
    """
    query = db.query(AuditLog).filter(AuditLog.user_id == current_user.user_id)
    if action:
        query = query.filter(AuditLog.action == action)

    total = query.count()
    items = (
        query.order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return DataResponse(
        data=AuditLogListResponse(
            items=[AuditLogOut.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )
    )
