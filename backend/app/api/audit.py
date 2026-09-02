import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.audit import AuditLogListResponse
from app.services.audit_service import audit_service

router = APIRouter(prefix="/api/audit", tags=["Audit Trail"])


@router.get(
    "/{customer_id}",
    response_model=AuditLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get customer audit log events",
)
def get_customer_audit_trail(
    customer_id: uuid.UUID,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves chronological audit events for the authenticated customer:
    - Enforces ownership: customer can only access their own audit trail.
    - Returns observable AI agent, cart, order, and payment activities.
    - Supports pagination and filtering by event_type.
    """
    if customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this customer's audit trail.",
        )
    logs, total = audit_service.get_customer_audit_logs(
        db=db,
        customer_id=customer_id,
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
