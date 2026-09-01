from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class CreatePaymentOrderRequest(BaseModel):
    order_id: UUID = Field(..., description="UUID of application order to initiate Razorpay checkout for")
    customer_id: Optional[UUID] = Field(
        default=None,
        description="Optional customer UUID for customer-order validation.",
    )

    # Strictly ignore any client-supplied monetary amounts
    model_config = ConfigDict(extra="ignore")


class PaymentOrderResponse(BaseModel):
    payment_id: UUID
    order_id: UUID
    razorpay_order_id: str
    amount: Decimal
    amount_in_paise: int
    currency: str
    key_id: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
