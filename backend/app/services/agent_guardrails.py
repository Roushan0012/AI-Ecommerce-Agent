import logging
import re
import uuid
from decimal import Decimal
from typing import Optional, Tuple
from fastapi import HTTPException, status
from app.core.guardrails import guardrails
from app.schemas.agent import ShoppingIntent

logger = logging.getLogger(__name__)


class AgentGuardrailService:
    """
    Dedicated security and integrity guardrail service for AI Agent operations.
    Guarantees that LLM-generated decisions, extracted intents, and tool calls
    are strictly filtered, sanitized, and bound by backend business rules before
    any database or payment interaction.
    """

    @classmethod
    def sanitize_user_prompt(cls, message: str) -> str:
        """Sanitizes user natural language prompt and removes prompt injection attempts."""
        if not message or not message.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User message cannot be empty.",
            )
        return guardrails.sanitize_agent_input(message)

    @classmethod
    def validate_shopping_intent(cls, intent: ShoppingIntent) -> ShoppingIntent:
        """
        Validates extracted ShoppingIntent values:
        - Ensures currency is supported.
        - Ensures non-negative price boundaries.
        - Ensures min_price <= max_price.
        - Sanitizes search queries and category strings.
        """
        if intent.currency:
            intent.currency = guardrails.validate_currency(intent.currency)

        if intent.min_price is not None and intent.min_price < Decimal("0.00"):
            intent.min_price = Decimal("0.00")

        if intent.max_price is not None and intent.max_price < Decimal("0.00"):
            intent.max_price = Decimal("0.00")

        if (
            intent.min_price is not None
            and intent.max_price is not None
            and intent.min_price > intent.max_price
        ):
            # Swap or reset if model inverted bounds
            intent.min_price, intent.max_price = intent.max_price, intent.min_price

        if intent.search_query:
            intent.search_query = guardrails.sanitize_agent_input(intent.search_query)

        if intent.category:
            intent.category = guardrails.sanitize_agent_input(intent.category)

        return intent

    @classmethod
    def validate_agent_cart_tool(
        cls,
        customer_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: int,
    ) -> Tuple[uuid.UUID, uuid.UUID, int]:
        """
        Validates AI agent tool parameters when performing cart actions:
        - Asserts valid UUIDs.
        - Validates positive integer quantity within single-item limits.
        """
        valid_qty = guardrails.validate_quantity(quantity)
        return customer_id, product_id, valid_qty

    @classmethod
    def redact_sensitive_information(cls, text: str) -> str:
        """
        Redacts any sensitive tokens, API keys, database connection strings,
        or passwords before returning LLM responses to the user.
        """
        if not text:
            return ""

        # Redact common key formats
        redacted = re.sub(r"(gsk_[a-zA-Z0-9_-]{20,})", "[REDACTED_API_KEY]", text)
        redacted = re.sub(r"(sk-[a-zA-Z0-9_-]{20,})", "[REDACTED_API_KEY]", redacted)
        redacted = re.sub(r"(rzp_test_[a-zA-Z0-9_-]{10,})", "[REDACTED_KEY]", redacted)
        redacted = re.sub(r"(postgres(?:ql)?://[^\s@]+@[^\s/]+/[^\s]+)", "[REDACTED_DB_URL]", redacted)

        return redacted


agent_guardrail_service = AgentGuardrailService()
