import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    """
    Structured, backend-authoritative audit log table for AI-agent and commerce actions.
    Records WHAT happened, WHEN, WHO, WHICH tool/action, and execution status.
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    action: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="success", nullable=False, index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    cart_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    payment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, event_type='{self.event_type}', action='{self.action}', status='{self.status}', customer_id={self.customer_id})>"
