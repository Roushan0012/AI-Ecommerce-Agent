from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ShoppingIntent(BaseModel):
    intent: Literal["product_search", "general", "inquiry"] = Field(
        default="product_search",
        description="Type of user intent (product_search, general, inquiry)",
    )
    search_query: Optional[str] = Field(
        default=None,
        description="Extracted search keywords for catalog query",
    )
    category: Optional[str] = Field(
        default=None,
        description="Extracted product category (e.g. Audio, Computer Accessories, Chargers & Cables, Work & Travel)",
    )
    min_price: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Minimum price filter in INR if requested",
    )
    max_price: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Maximum price filter in INR if requested",
    )
    currency: str = Field(
        default="INR",
        description="Currency code, defaults to INR",
    )
    availability_required: bool = Field(
        default=True,
        description="Whether only in-stock available products are requested",
    )

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="after")
    def validate_price_bounds(self) -> "ShoppingIntent":
        if self.min_price is not None and self.max_price is not None:
            if self.min_price > self.max_price:
                raise ValueError("min_price cannot be greater than max_price")
        return self


class AgentUnderstandRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Customer natural-language shopping message",
    )

    @field_validator("message")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message cannot be empty or only whitespace")
        return stripped


class AgentUnderstandResponse(BaseModel):
    message: str = Field(
        ...,
        description="Assistant conversational summary of understood intent",
    )
    intent: ShoppingIntent = Field(
        ...,
        description="Structured shopping intent",
    )
