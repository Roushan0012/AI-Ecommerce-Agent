import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
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
    db: Session = Depends(get_db),
):
    """
    Retrieves chronological audit events for the given customer:
    - Returns observable AI agent, cart, order, and payment activities.
    - Prevents cross-customer data leakage.
    - Supports pagination and filtering by event_type.
    """
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
