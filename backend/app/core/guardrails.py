import logging
import re
import uuid
from decimal import Decimal
from typing import Optional, Set
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

ALLOWED_CURRENCIES: Set[str] = {"INR"}
VALID_ORDER_STATUSES: Set[str] = {"pending_payment", "created", "paid", "cancelled", "failed"}
VALID_CART_STATUSES: Set[str] = {"active", "converted", "abandoned"}


class GuardrailViolationError(HTTPException):
    """Specific exception raised when a security guardrail is breached."""

    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


class CommerceGuardrails:
    """
    Centralized Security & Guardrails enforcement layer for commerce and agent operations.
    Ensures that LLMs, client requests, and third-party inputs can never bypass authoritative
    backend business logic, database pricing, or order state machines.
    """

    @staticmethod
    def validate_quantity(quantity: int, min_limit: int = 1, max_limit: int = 500) -> int:
        """
        Guards against invalid, zero, negative, or absurdly large order quantities.
        """
        if not isinstance(quantity, int):
            raise GuardrailViolationError(
                detail="Quantity must be an integer.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        if quantity < min_limit:
            raise GuardrailViolationError(
                detail=f"Quantity must be at least {min_limit}.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if quantity > max_limit:
            raise GuardrailViolationError(
                detail=f"Requested quantity {quantity} exceeds single-item maximum limit of {max_limit}.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return quantity

    @staticmethod
    def validate_currency(currency: str) -> str:
        """
        Guards against unsupported currency manipulations.
        """
        if not currency or currency.upper() not in ALLOWED_CURRENCIES:
            raise GuardrailViolationError(
                detail=f"Unsupported currency '{currency}'. Allowed: {', '.join(ALLOWED_CURRENCIES)}.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return currency.upper()

    @staticmethod
    def validate_customer_ownership(
        resource_customer_id: uuid.UUID,
        requesting_customer_id: Optional[uuid.UUID],
        resource_name: str = "Resource",
    ) -> None:
        """
        Guards against cross-customer resource access / data tampering.
        """
        if requesting_customer_id is not None and resource_customer_id != requesting_customer_id:
            logger.warning(
                f"Security Guardrail Alert: Customer '{requesting_customer_id}' attempted unauthorized access to {resource_name} owned by '{resource_customer_id}'."
            )
            # Return 404 to avoid leaking resource existence
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{resource_name} not found for this customer.",
            )

    @staticmethod
    def validate_order_state_transition(
        current_status: str,
        target_status: str,
        is_webhook_verified: bool = False,
    ) -> None:
        """
        Strict finite state machine guardrail for Orders.
        Direct transitions to 'paid' by clients or AI agents are strictly rejected.
        """
        current_status = current_status.lower()
        target_status = target_status.lower()

        if target_status not in VALID_ORDER_STATUSES:
            raise GuardrailViolationError(
                detail=f"Invalid target order status '{target_status}'.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Guard against direct 'paid' transition without cryptographic webhook verification
        if target_status == "paid" and not is_webhook_verified:
            logger.error(
                "Security Guardrail Violation: Unauthorized attempt to mark order as 'paid' without cryptographic webhook verification."
            )
            raise GuardrailViolationError(
                detail="Orders can only be marked as 'paid' through verified payment gateway webhooks.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # 2. Immutable Terminal States
        if current_status == "paid" and target_status != "paid":
            raise GuardrailViolationError(
                detail="Order has already been paid and settled. Status cannot be modified.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if current_status == "cancelled":
            raise GuardrailViolationError(
                detail="Order has been cancelled and cannot transition to any other state.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Allowed Transitions:
        # created / pending_payment -> paid (webhook only)
        # created / pending_payment -> failed
        # created / pending_payment -> cancelled
        valid_transitions = {
            "created": {"pending_payment", "cancelled", "paid"},
            "pending_payment": {"paid", "failed", "cancelled"},
            "failed": {"pending_payment", "cancelled"},
            "paid": set(),
            "cancelled": set(),
        }

        allowed_targets = valid_transitions.get(current_status, set())
        if target_status not in allowed_targets and target_status != current_status:
            raise GuardrailViolationError(
                detail=f"Invalid order state transition from '{current_status}' to '{target_status}'.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    @staticmethod
    def calculate_authoritative_total(
        subtotal: Decimal,
        discount: Decimal = Decimal("0.00"),
    ) -> Decimal:
        """
        Computes authoritative backend total ensuring non-negative invariant.
        """
        if subtotal < Decimal("0.00"):
            raise GuardrailViolationError(
                detail="Subtotal cannot be negative.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if discount < Decimal("0.00"):
            discount = Decimal("0.00")

        total = subtotal - discount
        return max(Decimal("0.00"), total)

    @staticmethod
    def sanitize_agent_input(text: str) -> str:
        """
        Sanitizes natural language prompt inputs against prompt injection and control sequence injection.
        """
        if not text:
            return ""

        cleaned = text.strip()

        # Remove ASCII control characters (except common whitespace)
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", cleaned)

        # Prevent prompt escape sequences (e.g. system override tags)
        dangerous_tags = [
            r"<\s*system\s*>",
            r"<\s*/\s*system\s*>",
            r"<\s*instruction\s*>",
            r"<\s*/\s*instruction\s*>",
            r"\[\s*SYSTEM\s*\]",
            r"\[\s*/\s*SYSTEM\s*\]",
        ]
        for tag in dangerous_tags:
            cleaned = re.sub(tag, "", cleaned, flags=re.IGNORECASE)

        return cleaned.strip()


guardrails = CommerceGuardrails()
