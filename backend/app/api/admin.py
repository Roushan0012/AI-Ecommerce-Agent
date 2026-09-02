import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.database import check_database_connection, get_db
from app.core.dependencies import require_admin
from app.models.order import Order
from app.models.user import User
from app.schemas.audit import AuditLogListResponse
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],
)


@router.get(
    "/system/status",
    status_code=status.HTTP_200_OK,
    summary="Get system health and platform administrative statistics",
)
def get_system_status(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Returns platform health, database connectivity status, and user role distribution.
    Strictly restricted to users with the 'admin' role.
    """
    is_connected = check_database_connection()

    role_counts = {}
    try:
        results = db.execute(
            select(User.role, func.count(User.id)).group_by(User.role)
        ).all()
        for role_name, count in results:
            role_counts[role_name] = count
    except Exception as exc:
        logger.warning(f"Error querying role counts: {exc}")

    total_orders = 0
    try:
        total_orders = db.execute(select(func.count(Order.id))).scalar_one()
    except Exception as exc:
        logger.warning(f"Error querying order count: {exc}")

    return {
        "status": "ok",
        "service": "ai-commerce-agent-admin",
        "database": "connected" if is_connected else "disconnected",
        "admin_user": current_admin.email,
        "users_by_role": role_counts,
        "total_orders": total_orders,
    }


@router.get(
    "/audit-logs",
    response_model=AuditLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="List platform-wide audit log events",
)
def get_admin_audit_logs(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Retrieves chronological audit events platform-wide across all users and agents.
    Strictly restricted to users with the 'admin' role.
    """
    logs, total = audit_service.get_all_audit_logs(
        db=db,
        event_type=event_type,
        page=page,
        page_size=page_size,
    )
    return audit_service.format_audit_list_response(
        logs=logs,
        total=total,
        page=page,
        page_size=page_size,
    )
