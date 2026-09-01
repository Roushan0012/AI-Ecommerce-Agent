import hashlib
import hmac
import logging
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional
from fastapi import HTTPException, status
import razorpay
from app.core.config import settings

logger = logging.getLogger(__name__)


class RazorpayService:
    """Dedicated service for Razorpay Test Mode integration and order creation."""

    def __init__(self):
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET
        self.currency = settings.RAZORPAY_CURRENCY
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

    def _get_client(self) -> Optional[razorpay.Client]:
        """Instantiates Razorpay Client if credentials are provided."""
        if self.key_id and self.key_secret and self.key_id != "rzp_test_placeholder":
            try:
                return razorpay.Client(auth=(self.key_id, self.key_secret))
            except Exception as e:
                logger.error(f"Failed to initialize Razorpay client: {e}")
                return None
        return None

    def get_public_key_id(self) -> str:
        """Returns the public key ID required by frontend Razorpay Checkout."""
        return self.key_id or "rzp_test_placeholder"

    def verify_webhook_signature(self, raw_body: bytes, signature: str) -> bool:
        """
        Verifies the HMAC-SHA256 signature of a Razorpay webhook payload against the webhook secret.
        Uses constant-time comparison to prevent timing attacks.
        """
        if not signature or not self.webhook_secret:
            return False

        try:
            expected_signature = hmac.new(
                key=self.webhook_secret.encode("utf-8"),
                msg=raw_body,
                digestmod=hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(expected_signature, signature)
        except Exception as exc:
            logger.error(f"Error verifying webhook signature: {exc}")
            return False

    def generate_webhook_signature(self, raw_body: bytes) -> str:
        """
        Generates HMAC-SHA256 signature for test execution and verification.
        """
        secret = self.webhook_secret or "test_webhook_secret_key_123"
        return hmac.new(
            key=secret.encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha256,
        ).hexdigest()

    def create_razorpay_order(
        self,
        amount: Decimal,
        currency: str = "INR",
        receipt: Optional[str] = None,
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Creates a Razorpay Test Mode order for the given authoritative amount.
        - Converts monetary amount to smallest currency unit (paise for INR).
        - Connects to Razorpay API or uses mock test mode when credentials are test placeholders.
        """
        if amount <= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order total must be greater than zero to initiate payment.",
            )

        # Convert to paise (e.g. ₹4999.00 -> 499900 paise)
        amount_in_paise = int(round(float(amount) * 100))
        if amount_in_paise < 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Minimum payable amount is ₹1.00 (100 paise).",
            )

        if not receipt:
            receipt = f"rcpt_{uuid.uuid4().hex[:12]}"

        client = self._get_client()

        if client:
            try:
                payload = {
                    "amount": amount_in_paise,
                    "currency": currency,
                    "receipt": receipt,
                    "notes": notes or {},
                    "payment_capture": 1,
                }
                logger.info(f"Initiating Razorpay order creation for amount={amount_in_paise} paise")
                rzp_order = client.order.create(data=payload)
                return rzp_order
            except Exception as exc:
                logger.error(f"Razorpay API call failed: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Razorpay API order creation failed: {str(exc)}",
                )
        else:
            # Deterministic test order creation for offline / mock test execution
            rzp_order_id = f"order_test_{uuid.uuid4().hex[:14]}"
            return {
                "id": rzp_order_id,
                "entity": "order",
                "amount": amount_in_paise,
                "amount_paid": 0,
                "amount_due": amount_in_paise,
                "currency": currency,
                "receipt": receipt,
                "status": "created",
                "attempts": 0,
                "notes": notes or {},
                "created_at": int(time.time()),
            }


razorpay_service = RazorpayService()
