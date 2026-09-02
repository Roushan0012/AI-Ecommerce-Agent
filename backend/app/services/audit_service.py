import logging
import re
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogListResponse, AuditLogResponse

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {
    "password",
    "secret",
    "token",
    "authorization",
    "api_key",
    "key_secret",
    "webhook_secret",
    "signature",
    "x-razorpay-signature",
    "database_url",
    "credentials",
}


class AuditService:
    """
    Backend-authoritative service for capturing and retrieving audit trail events.
    Captures WHAT happened, WHEN, WHO, WHICH tool/action, and execution status.
    Guarantees non-critical resilience: an audit logging failure will not crash
    commerce operations or payment settlements.
    """

    @classmethod
    def sanitize_and_redact(cls, data: Any) -> Any:
        """
        Recursively redacts sensitive API keys, tokens, secrets, and formats
        non-serializable types (Decimal, UUID) for audit storage.
        """
        if data is None:
            return None

        if isinstance(data, dict):
            sanitized_dict = {}
            for k, v in data.items():
                k_lower = str(k).lower()
                if any(sens in k_lower for sens in SENSITIVE_KEYS):
                    sanitized_dict[k] = "[REDACTED]"
                else:
                    sanitized_dict[k] = cls.sanitize_and_redact(v)
            return sanitized_dict

        if isinstance(data, (list, tuple, set)):
            return [cls.sanitize_and_redact(item) for item in data]

        if isinstance(data, (uuid.UUID, Decimal)):
            return str(data)

        if isinstance(data, str):
            # Redact common key patterns & connection strings
            redacted = re.sub(r"(gsk_[a-zA-Z0-9_-]{20,})", "[REDACTED_API_KEY]", data)
            redacted = re.sub(r"(sk-[a-zA-Z0-9_-]{20,})", "[REDACTED_API_KEY]", redacted)
            redacted = re.sub(r"(rzp_test_[a-zA-Z0-9_-]{10,})", "[REDACTED_KEY]", redacted)
            redacted = re.sub(
                r"(postgres(?:ql)?://[^\s@]+@[^\s/]+/[^\s]+)",
                "[REDACTED_DB_URL]",
                redacted,
            )
            # Strip prompt injection tags
            redacted = re.sub(r"<\s*/?\s*(system|instruction)\s*>", "", redacted, flags=re.IGNORECASE)
            return redacted

        return data

    @classmethod
    def record_event(
        cls,
        db: Session,
        event_type: str,
        customer_id: Optional[uuid.UUID] = None,
        session_id: Optional[str] = None,
        action: Optional[str] = None,
        payload: Optional[Any] = None,
        result: Optional[Any] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        cart_id: Optional[uuid.UUID] = None,
        order_id: Optional[uuid.UUID] = None,
        payment_id: Optional[uuid.UUID] = None,
    ) -> Optional[AuditLog]:
        """
        Creates and persists a structured audit event.
        Fails safely if audit storage encounters an error without disrupting main execution.
        """
        try:
            sanitized_payload = cls.sanitize_and_redact(payload)
            sanitized_result = cls.sanitize_and_redact(result)

            if isinstance(sanitized_payload, (str, int, float, bool, list)):
                sanitized_payload = {"data": sanitized_payload}
            if isinstance(sanitized_result, (str, int, float, bool, list)):
                sanitized_result = {"data": sanitized_result}

            audit_entry = AuditLog(
                id=uuid.uuid4(),
                customer_id=customer_id,
                session_id=session_id,
                event_type=event_type,
                action=action,
                payload=sanitized_payload,
                result=sanitized_result,
                status=status,
                error_message=error_message,
                cart_id=cart_id,
                order_id=order_id,
                payment_id=payment_id,
            )
            db.add(audit_entry)
            db.commit()
            db.refresh(audit_entry)
            return audit_entry
        except Exception as exc:
            logger.warning(f"Failed to persist audit event '{event_type}': {exc}")
            try:
                db.rollback()
            except Exception:
                pass
            return None

    @classmethod
    def get_customer_audit_logs(
        cls,
        db: Session,
        customer_id: uuid.UUID,
        event_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[AuditLog], int]:
        """
        Retrieves paginated audit events for a customer, sorted newest first.
        """
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        offset = (page - 1) * page_size

        query = select(AuditLog).where(AuditLog.customer_id == customer_id)
        count_query = select(func.count(AuditLog.id)).where(AuditLog.customer_id == customer_id)

        if event_type:
            query = query.where(AuditLog.event_type == event_type)
            count_query = count_query.where(AuditLog.event_type == event_type)

        query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)

        logs = list(db.execute(query).scalars().all())
        total_count = db.execute(count_query).scalar_one()

        return logs, total_count

    @classmethod
    def get_all_audit_logs(
        cls,
        db: Session,
        event_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[AuditLog], int]:
        """
        Retrieves paginated platform-wide audit events across all customers, sorted newest first.
        Strictly for administrative audits.
        """
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        offset = (page - 1) * page_size

        query = select(AuditLog)
        count_query = select(func.count(AuditLog.id))

        if event_type:
            query = query.where(AuditLog.event_type == event_type)
            count_query = count_query.where(AuditLog.event_type == event_type)

        query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)

        logs = list(db.execute(query).scalars().all())
        total_count = db.execute(count_query).scalar_one()

        return logs, total_count

    @classmethod
    def format_audit_response(cls, log: AuditLog) -> AuditLogResponse:
        """Formats AuditLog SQLAlchemy model into response schema."""
        return AuditLogResponse(
            id=log.id,
            customer_id=log.customer_id,
            session_id=log.session_id,
            event_type=log.event_type,
            action=log.action,
            payload=log.payload,
            result=log.result,
            status=log.status,
            error_message=log.error_message,
            cart_id=log.cart_id,
            order_id=log.order_id,
            payment_id=log.payment_id,
            created_at=log.created_at,
        )

    @classmethod
    def format_audit_list_response(
        cls,
        logs: List[AuditLog],
        total: int,
        page: int,
        page_size: int,
    ) -> AuditLogListResponse:
        """Formats a list of AuditLog records into paginated schema."""
        return AuditLogListResponse(
            items=[cls.format_audit_response(l) for l in logs],
            total=total,
            page=page,
            page_size=page_size,
        )


audit_service = AuditService()
