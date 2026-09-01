import logging
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.guardrails import guardrails
from app.models.order import Order
from app.models.payment import Payment
from app.schemas.payment import PaymentOrderResponse
from app.services.razorpay_service import razorpay_service

logger = logging.getLogger(__name__)


class PaymentService:
    """Service managing payment initiation, persistence, and webhook verification for orders."""

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
        # 1. Authoritative Order Lookup & Guardrail Ownership Check
        stmt = select(Order).where(Order.id == order_id)
        order = db.execute(stmt).scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with ID '{order_id}' not found.",
            )

        guardrails.validate_customer_ownership(order.customer_id, customer_id, "Order")

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

        from app.services.audit_service import audit_service
        audit_service.record_event(
            db=db,
            event_type="PAYMENT_EVENT",
            customer_id=order.customer_id,
            action="create_payment_order",
            order_id=order.id,
            payment_id=payment.id,
            payload={"order_id": str(order.id), "amount": str(payment.amount), "currency": payment.currency},
            result={"payment_id": str(payment.id), "razorpay_order_id": razorpay_order_id, "status": payment.status},
            status="success",
        )

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

    @classmethod
    def process_webhook_event(
        cls,
        db: Session,
        event_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Processes a verified Razorpay webhook event:
        - Validates event structure and extracts order/payment entities.
        - Matches event with authoritative internal Order and Payment records.
        - Enforces amount and currency reconciliation against database records.
        - Handles duplicate events idempotently without double-updating.
        - Updates Payment and Order statuses appropriately.
        """
        event = event_payload.get("event", "")
        payload_data = event_payload.get("payload", {})
        payment_entity = payload_data.get("payment", {}).get("entity", {})
        order_entity = payload_data.get("order", {}).get("entity", {})

        razorpay_order_id = payment_entity.get("order_id") or order_entity.get("id")
        razorpay_payment_id = payment_entity.get("id")

        if not razorpay_order_id:
            logger.warning(f"Webhook event '{event}' missing razorpay_order_id in payload.")
            return {
                "status": "ignored",
                "event": event,
                "reason": "Missing razorpay_order_id in webhook payload",
            }

        # 1. Database Lookup
        stmt = (
            select(Payment)
            .where(Payment.razorpay_order_id == razorpay_order_id)
            .order_by(Payment.created_at.desc())
        )
        payment = db.execute(stmt).scalars().first()

        if not payment:
            # Fallback: check by Order.razorpay_order_id
            order_stmt = select(Order).where(Order.razorpay_order_id == razorpay_order_id)
            order = db.execute(order_stmt).scalar_one_or_none()
            if not order:
                logger.warning(
                    f"Received webhook event '{event}' for unknown Razorpay order '{razorpay_order_id}'."
                )
                return {
                    "status": "ignored",
                    "event": event,
                    "reason": f"No order found matching razorpay_order_id '{razorpay_order_id}'",
                }
        else:
            order = payment.order or db.execute(
                select(Order).where(Order.id == payment.order_id)
            ).scalar_one_or_none()

        # 2. Idempotency Check
        if payment and payment.status == "paid" and event in ["payment.captured", "order.paid", "payment.authorized"]:
            logger.info(
                f"Duplicate webhook event '{event}' received for already paid payment '{payment.id}'."
            )
            return {
                "status": "ok",
                "event": event,
                "message": "Payment already verified and marked paid.",
                "idempotent": True,
                "payment_id": str(payment.id),
                "order_id": str(order.id) if order else None,
                "order_status": order.status if order else "paid",
            }

        # 3. Handle Payment Captured / Order Paid
        if event in ["payment.captured", "order.paid", "payment.authorized"]:
            event_amount = payment_entity.get("amount") or order_entity.get("amount")
            event_currency = payment_entity.get("currency") or order_entity.get("currency") or "INR"

            from app.services.audit_service import audit_service

            # Reconcile Currency
            if payment and event_currency.upper() != payment.currency.upper():
                logger.error(
                    f"Payment currency mismatch for order {order.id}: expected {payment.currency}, got {event_currency}"
                )
                payment.status = "failed"
                db.commit()
                audit_service.record_event(
                    db=db,
                    event_type="SECURITY_VIOLATION",
                    customer_id=order.customer_id if order else None,
                    action="webhook_currency_mismatch",
                    order_id=order.id if order else None,
                    payment_id=payment.id,
                    payload={"expected_currency": payment.currency, "received_currency": event_currency},
                    status="rejected",
                    error_message=f"Currency mismatch: expected {payment.currency}, received {event_currency}",
                )
                return {
                    "status": "error",
                    "event": event,
                    "message": f"Currency mismatch: expected {payment.currency}, received {event_currency}",
                }

            # Reconcile Amount (Authoritative DB check)
            if payment and event_amount is not None:
                expected_amount_in_paise = int(round(float(payment.amount) * 100))
                if int(event_amount) != expected_amount_in_paise:
                    logger.error(
                        f"Payment amount mismatch for order {order.id}: expected {expected_amount_in_paise} paise, got {event_amount} paise"
                    )
                    payment.status = "failed"
                    db.commit()
                    audit_service.record_event(
                        db=db,
                        event_type="SECURITY_VIOLATION",
                        customer_id=order.customer_id if order else None,
                        action="webhook_amount_mismatch",
                        order_id=order.id if order else None,
                        payment_id=payment.id,
                        payload={"expected_amount_paise": expected_amount_in_paise, "received_amount_paise": event_amount},
                        status="rejected",
                        error_message=f"Amount mismatch: expected {expected_amount_in_paise} paise, received {event_amount} paise",
                    )
                    return {
                        "status": "error",
                        "event": event,
                        "message": f"Amount mismatch: expected {expected_amount_in_paise} paise, received {event_amount} paise",
                    }

            # Mark Payment as Paid
            if payment:
                payment.status = "paid"
                if razorpay_payment_id:
                    payment.razorpay_payment_id = razorpay_payment_id

            # Mark Order as Paid
            if order:
                order.status = "paid"

            db.commit()
            if payment:
                db.refresh(payment)
            if order:
                db.refresh(order)

            audit_service.record_event(
                db=db,
                event_type="PAYMENT_EVENT",
                customer_id=order.customer_id if order else None,
                action="payment_verified_and_paid",
                order_id=order.id if order else None,
                payment_id=payment.id if payment else None,
                payload={"event": event, "razorpay_order_id": razorpay_order_id, "razorpay_payment_id": razorpay_payment_id},
                result={"order_status": "paid", "payment_status": "paid"},
                status="success",
            )

            logger.info(f"Payment successfully verified and order '{order.id if order else None}' marked as paid.")
            return {
                "status": "ok",
                "event": event,
                "message": "Payment verified and order marked as paid.",
                "payment_id": str(payment.id) if payment else None,
                "order_id": str(order.id) if order else None,
                "order_status": "paid",
                "payment_status": "paid",
            }

        # 4. Handle Payment Failed
        elif event == "payment.failed":
            if payment:
                payment.status = "failed"
                if razorpay_payment_id:
                    payment.razorpay_payment_id = razorpay_payment_id

            # Keep order status as pending_payment (do not mark paid)
            db.commit()
            if payment:
                db.refresh(payment)

            logger.warning(f"Payment failure recorded for order '{order.id if order else None}'.")
            return {
                "status": "ok",
                "event": event,
                "message": "Payment failure recorded.",
                "payment_id": str(payment.id) if payment else None,
                "order_id": str(order.id) if order else None,
                "payment_status": "failed",
                "order_status": order.status if order else "pending_payment",
            }

        # 5. Unhandled Events
        return {
            "status": "ignored",
            "event": event,
            "message": "Event received and ignored.",
        }


payment_service = PaymentService()
