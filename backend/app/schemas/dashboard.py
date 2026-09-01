import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class OverviewMetricsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_revenue: Decimal = Field(..., description="Authoritative sum of paid order totals")
    paid_orders_count: int = Field(..., ge=0, description="Count of completed/paid orders")
    total_orders_count: int = Field(..., ge=0, description="Count of all orders across statuses")
    average_order_value: Decimal = Field(..., description="Average revenue per paid order")
    conversion_rate: float = Field(..., ge=0, le=100, description="Conversion rate percentage (paid orders / carts)")
    ai_assisted_orders_count: int = Field(..., ge=0, description="Number of paid orders assisted by AI agent interactions")
    ai_assisted_revenue: Decimal = Field(..., description="Total revenue generated from AI-assisted paid orders")
    ai_assisted_percentage: float = Field(..., ge=0, le=100, description="Percentage of paid orders assisted by AI")
    recommendations_generated: int = Field(..., ge=0, description="Number of recommendation/growth events generated")
    recommendations_accepted: int = Field(..., ge=0, description="Number of recommendations that led to cart/order conversions")
    recommendation_acceptance_rate: float = Field(..., ge=0, le=100, description="Percentage of recommendations converted")
    upsell_count: int = Field(..., ge=0, description="Number of higher-tier upgrade items purchased")
    upsell_revenue: Decimal = Field(..., description="Revenue attributed to upsell product selections")
    cross_sell_count: int = Field(..., ge=0, description="Number of accessory companion items purchased")
    cross_sell_revenue: Decimal = Field(..., description="Revenue attributed to cross-sell accessory companion selections")
    currency: str = Field(default="INR", description="Standard currency code")


class DashboardOrderItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    total: Decimal
    currency: str
    status: str
    payment_status: Optional[str] = None
    items_count: int = 0
    is_ai_assisted: bool = False
    created_at: datetime


class DashboardOrdersResponse(BaseModel):
    items: List[DashboardOrderItem]
    total: int = Field(..., ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1)


class DashboardActivityItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    action: Optional[str] = None
    status: str
    customer_id: Optional[uuid.UUID] = None
    cart_id: Optional[uuid.UUID] = None
    order_id: Optional[uuid.UUID] = None
    error_message: Optional[str] = None
    created_at: datetime


class DashboardActivityResponse(BaseModel):
    items: List[DashboardActivityItem]
    total: int = Field(..., ge=0)
