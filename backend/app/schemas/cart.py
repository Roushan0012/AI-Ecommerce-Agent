from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class CartItemCreateRequest(BaseModel):
    product_id: UUID = Field(..., description="UUID of the product to add to cart")
    quantity: int = Field(1, gt=0, le=1000, description="Quantity to add (must be positive integer)")

    # Explicitly ignore/disallow client price override
    model_config = ConfigDict(extra="ignore")


class CartItemUpdateRequest(BaseModel):
    quantity: int = Field(..., gt=0, le=1000, description="New quantity for cart item (must be positive integer)")

    model_config = ConfigDict(extra="ignore")


class CartItemResponse(BaseModel):
    id: UUID
    cart_id: UUID
    product_id: UUID
    product_name: str
    sku: str
    category: Optional[str] = None
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CartCreateRequest(BaseModel):
    customer_id: Optional[UUID] = Field(
        default=None,
        description="Optional customer UUID. If not provided, a new customer ID is assigned.",
    )

    model_config = ConfigDict(extra="ignore")


class CartResponse(BaseModel):
    id: UUID
    customer_id: UUID
    status: str
    currency: str
    items: List[CartItemResponse] = Field(default_factory=list)
    item_count: int
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
