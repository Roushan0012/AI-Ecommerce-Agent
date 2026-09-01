import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.payment import (
    CreatePaymentOrderRequest,
    PaymentOrderResponse,
)
from app.services.payment_service import payment_service

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
    db: Session = Depends(get_db),
):
    """
    Creates a Razorpay Test Mode checkout order for an existing application order:
    - Verifies order exists and is in 'pending_payment' or 'created' status.
    - Reads authoritative payable total from database (rejects client amounts).
    - Generates Razorpay order in INR.
    - Saves payment record reference in database.
    - Returns Razorpay checkout payload (key_id, razorpay_order_id, amount_in_paise).
    """
    payment_order = payment_service.create_payment_order(
        db,
        order_id=payload.order_id,
        customer_id=payload.customer_id,
    )
    return payment_order
