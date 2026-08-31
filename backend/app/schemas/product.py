from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    category: Optional[str] = Field(None, description="Product category")
    price: Decimal = Field(..., ge=0, description="Product price in INR")
    currency: str = Field("INR", description="Currency code (e.g. INR)")
    inventory: int = Field(0, ge=0, description="Available stock quantity")
    sku: str = Field(..., description="Stock keeping unit, unique per merchant")
    attributes: Dict[str, Any] = Field(
        default_factory=dict, description="Product metadata and attributes"
    )
    is_active: bool = Field(True, description="Whether product is active")


class ProductResponse(ProductBase):
    id: UUID = Field(..., description="Unique product ID")
    merchant_id: UUID = Field(..., description="Merchant ID owning this product")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    items: List[ProductResponse] = Field(..., description="List of products")
    total: int = Field(..., ge=0, description="Total matching products count")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Items per page")
