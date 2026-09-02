import json
import logging
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.payment import (
    CreatePaymentOrderRequest,
    PaymentOrderResponse,
)
from app.services.payment_service import payment_service
from app.services.razorpay_service import razorpay_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["Payments"])


@router.post(
    "/create-order",
    response_model=PaymentOrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Create Razorpay Test Mode Order from backend Order",
)
def create_payment_order(
    payload: CreatePaymentOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Creates a Razorpay Test Mode checkout order for an existing application order:
    - Enforces ownership: user can only initiate payment for their own order.
    - Verifies order exists and is in 'pending_payment' or 'created' status.
    - Reads authoritative payable total from database (rejects client amounts).
    - Generates Razorpay order in INR.
    - Saves payment record reference in database.
    - Returns Razorpay checkout payload (key_id, razorpay_order_id, amount_in_paise).
    """
    if payload.customer_id and payload.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot initiate payment for another user's order.",
        )
    effective_customer_id = payload.customer_id or current_user.id
    payment_order = payment_service.create_payment_order(
        db,
        order_id=payload.order_id,
        customer_id=effective_customer_id,
    )
    return payment_order


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Razorpay Webhook Handler for Payment Verification",
)
async def handle_razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_razorpay_signature: str = Header(None, alias="X-Razorpay-Signature"),
):
    """
    Secure Razorpay Webhook Endpoint:
    1. Reads the raw request body before JSON parsing.
    2. Validates HMAC-SHA256 signature using RAZORPAY_WEBHOOK_SECRET.
    3. Rejects invalid or missing signatures with 400 Bad Request.
    4. Reconciles payment amount and currency against authoritative database record.
    5. Marks order and payment as 'paid' upon successful 'payment.captured' or 'order.paid' event.
    6. Handles duplicate deliveries idempotently.
    """
    body_bytes = await request.body()

    if not x_razorpay_signature:
        logger.warning("Webhook rejected: Missing 'X-Razorpay-Signature' header.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Razorpay-Signature header.",
        )

    is_valid = razorpay_service.verify_webhook_signature(
        raw_body=body_bytes,
        signature=x_razorpay_signature,
    )

    if not is_valid:
        logger.warning("Webhook rejected: Invalid signature.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature.",
        )

    try:
        event_payload = json.loads(body_bytes.decode("utf-8"))
    except Exception as exc:
        logger.error(f"Malformed JSON in webhook body: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON in request body.",
        )

    result = payment_service.process_webhook_event(db=db, event_payload=event_payload)
    return result
