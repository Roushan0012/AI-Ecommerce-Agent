from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class OrderCreateRequest(BaseModel):
    customer_id: UUID = Field(..., description="UUID of customer creating order from active cart")
    cart_id: Optional[UUID] = Field(
        default=None,
        description="Optional specific cart UUID. If not provided, the customer's current active cart is used.",
    )

    model_config = ConfigDict(extra="ignore")


class OrderItemResponse(BaseModel):
    id: UUID
    order_id: UUID
    product_id: UUID
    product_name: str
    sku: str
    unit_price: Decimal
    quantity: int
    total_price: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: UUID
    merchant_id: UUID
    customer_id: UUID
    cart_id: Optional[UUID] = None
    status: str
    currency: str
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    items: List[OrderItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    items: List[OrderResponse] = Field(default_factory=list)
    total: int
