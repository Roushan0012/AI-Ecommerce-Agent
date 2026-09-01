from typing import List, Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from app.schemas.agent import ShoppingIntent
from app.schemas.product import ProductResponse


class GrowthRecommendationItem(BaseModel):
    type: Literal["upsell", "cross_sell"] = Field(
        ...,
        description="Type of growth opportunity ('upsell' or 'cross_sell')",
    )
    product: ProductResponse = Field(
        ...,
        description="Recommended upgrade or complementary product details",
    )
    primary_product_id: UUID = Field(
        ...,
        description="ID of the primary product this recommendation relates to",
    )
    primary_product_name: str = Field(
        ...,
        description="Name of the primary product this recommendation relates to",
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Deterministic relevance and compatibility score (0.0 to 1.0)",
    )
    reason: str = Field(
        ...,
        description="Human-readable explanation of why this product is recommended",
    )


class AgentGrowthRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Customer natural-language shopping message or query",
    )
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(10, ge=1, le=100, description="Items per page")

    @field_validator("message")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message cannot be empty or only whitespace")
        return stripped


class AgentGrowthResponse(BaseModel):
    message: str = Field(
        ...,
        description="Conversational summary of growth recommendations",
    )
    intent: ShoppingIntent = Field(
        ...,
        description="Structured shopping intent derived from customer request",
    )
    primary_products: List[ProductResponse] = Field(
        default_factory=list,
        description="Primary matching products identified for the customer",
    )
    upsell: List[GrowthRecommendationItem] = Field(
        default_factory=list,
        description="Ranked upsell recommendations offering higher-value upgrades",
    )
    cross_sell: List[GrowthRecommendationItem] = Field(
        default_factory=list,
        description="Ranked cross-sell recommendations offering complementary accessories",
    )
    total: int = Field(
        0,
        ge=0,
        description="Total number of growth opportunities generated (upsell + cross_sell)",
    )
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(10, ge=1, description="Items per page")
