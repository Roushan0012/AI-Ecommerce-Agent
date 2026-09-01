import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.agent import ShoppingIntent
from app.schemas.product import ProductResponse


class AgentDiscoveryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Natural commerce search query")
    budget_max: Optional[Decimal] = Field(None, gt=0, description="Maximum budget filter")
    category: Optional[str] = Field(None, max_length=100, description="Optional product category")
    quantity: Optional[int] = Field(default=1, gt=0, le=100, description="Desired quantity")
    preferences: Optional[Dict[str, Any]] = Field(default=None, description="Optional structured preferences")


class AgentDiscoveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    intent: ShoppingIntent
    products: List[ProductResponse]
    total_matches: int
    authoritative_notice: str = "All prices and inventory quantities are backend-authoritative."


class AgentProductDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product: ProductResponse
    in_stock: bool
    available_inventory: int
    authoritative_price: Decimal
    currency: str


class AgentInventoryCheckRequest(BaseModel):
    product_id: uuid.UUID = Field(..., description="Target product UUID")
    quantity: int = Field(..., gt=0, le=1000, description="Requested purchase quantity")


class AgentInventoryCheckResponse(BaseModel):
    product_id: uuid.UUID
    available: bool
    current_inventory: int
    unit_price: Decimal
    currency: str
    status_message: str


class AgentCartItemRequest(BaseModel):
    customer_id: uuid.UUID = Field(..., description="Customer / session UUID")
    product_id: uuid.UUID = Field(..., description="Product UUID to add")
    quantity: int = Field(default=1, gt=0, le=1000, description="Quantity to add")
    idempotency_key: Optional[str] = Field(default=None, max_length=128, description="Optional idempotency key for safe retries")


class AgentOrderCreateRequest(BaseModel):
    customer_id: uuid.UUID = Field(..., description="Customer / session UUID")
    cart_id: uuid.UUID = Field(..., description="Active Cart UUID to checkout")
    idempotency_key: Optional[str] = Field(default=None, max_length=128, description="Optional idempotency key for safe retries")


class AgentPaymentInitiateRequest(BaseModel):
    order_id: uuid.UUID = Field(..., description="Order UUID to initiate payment for")
    customer_id: uuid.UUID = Field(..., description="Customer / session UUID")
    idempotency_key: Optional[str] = Field(default=None, max_length=128, description="Optional idempotency key")
