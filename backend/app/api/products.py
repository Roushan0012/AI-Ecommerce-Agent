from decimal import Decimal
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.product import ProductListResponse, ProductResponse
from app.services.product_service import product_service

router = APIRouter(prefix="/api/products", tags=["Products"])


@router.get("", response_model=ProductListResponse)
def list_products(
    search: Optional[str] = Query(
        None, description="Search keyword matching product name or description"
    ),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[Decimal] = Query(
        None, ge=0, description="Minimum price filter"
    ),
    max_price: Optional[Decimal] = Query(
        None, ge=0, description="Maximum price filter"
    ),
    available: Optional[bool] = Query(
        None, description="If true, only in-stock active products are returned"
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Page size (1-100)"),
    db: Session = Depends(get_db),
):
    # Validate min_price and max_price relationship
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price cannot be greater than max_price",
        )

    return product_service.list_products(
        db=db,
        search=search,
        category=category,
        min_price=min_price,
        max_price=max_price,
        available=available,
        page=page,
        page_size=page_size,
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: UUID,
    db: Session = Depends(get_db),
):
    product = product_service.get_product_by_id(db=db, product_id=product_id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return product
