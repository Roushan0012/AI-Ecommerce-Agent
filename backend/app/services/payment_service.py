import logging
import uuid
from decimal import Decimal
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.order import Order
from app.models.payment import Payment
from app.schemas.payment import PaymentOrderResponse
from app.services.razorpay_service import razorpay_service

logger = logging.getLogger(__name__)


class PaymentService:
    """Service managing payment initiation and persistence for backend orders."""

    @classmethod
    def create_payment_order(
        cls,
        db: Session,
        order_id: uuid.UUID,
        customer_id: Optional[uuid.UUID] = None,
    ) -> PaymentOrderResponse:
        """
        Creates a Razorpay Test Mode order for the given application order:
        1. Validates order existence and customer ownership.
        2. Validates order status eligibility (must be 'pending_payment' or 'created').
        3. Reads authoritative order.total from database (strictly ignores client amount).
        4. Calls RazorpayService to create checkout order in INR.
        5. Persists Payment record and attaches razorpay_order_id to Order.
        """
        # 1. Authoritative Order Lookup
        stmt = select(Order).where(Order.id == order_id)
        order = db.execute(stmt).scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with ID '{order_id}' not found.",
            )

        if customer_id and order.customer_id != customer_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found for this customer.",
            )

        # 2. Eligibility Validation
        if order.status == "paid":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order is already paid and cannot be paid again.",
            )

        if order.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order has been cancelled and is not eligible for payment.",
            )

        if order.status not in ["pending_payment", "created"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order status '{order.status}' is not eligible for payment checkout.",
            )

        # 3. Read authoritative amount
        authoritative_amount = order.total

        # 4. Call Razorpay Service
        receipt_ref = f"rcpt_{order.id.hex[:12]}"
        notes = {
            "application_order_id": str(order.id),
            "customer_id": str(order.customer_id),
            "environment": "test",
        }

        rzp_order = razorpay_service.create_razorpay_order(
            amount=authoritative_amount,
            currency=order.currency,
            receipt=receipt_ref,
            notes=notes,
        )

        razorpay_order_id = rzp_order["id"]

        # 5. Persist Payment Record & Update Order
        order.razorpay_order_id = razorpay_order_id

        payment = Payment(
            id=uuid.uuid4(),
            order_id=order.id,
            razorpay_order_id=razorpay_order_id,
            amount=authoritative_amount,
            currency=order.currency,
            status="created",
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        amount_in_paise = rzp_order.get(
            "amount", int(round(float(authoritative_amount) * 100))
        )
        key_id = razorpay_service.get_public_key_id()

        return PaymentOrderResponse(
            payment_id=payment.id,
            order_id=order.id,
            razorpay_order_id=razorpay_order_id,
            amount=payment.amount,
            amount_in_paise=amount_in_paise,
            currency=payment.currency,
            key_id=key_id,
            status=payment.status,
            created_at=payment.created_at,
        )


payment_service = PaymentService()
