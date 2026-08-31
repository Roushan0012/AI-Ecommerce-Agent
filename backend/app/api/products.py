from decimal import Decimal
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Product
from app.schemas.product import ProductListResponse, ProductResponse

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

    # Base query filters
    filters = []

    # Handle active & availability filtering
    if available is True:
        filters.append(Product.is_active.is_(True))
        filters.append(Product.inventory > 0)
    elif available is False:
        filters.append(or_(Product.is_active.is_(False), Product.inventory <= 0))
    else:
        filters.append(Product.is_active.is_(True))

    # Category filter (case-insensitive)
    if category and category.strip():
        filters.append(func.lower(Product.category) == category.strip().lower())

    # Search filter (case-insensitive on name or description)
    if search and search.strip():
        search_pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Product.name.ilike(search_pattern),
                Product.description.ilike(search_pattern),
            )
        )

    # Price filters
    if min_price is not None:
        filters.append(Product.price >= min_price)
    if max_price is not None:
        filters.append(Product.price <= max_price)

    # Total matching count
    count_query = select(func.count(Product.id)).where(*filters)
    total = db.execute(count_query).scalar() or 0

    # Query items with deterministic order
    offset = (page - 1) * page_size
    query = (
        select(Product)
        .where(*filters)
        .order_by(Product.name.asc(), Product.id.asc())
        .offset(offset)
        .limit(page_size)
    )
    items = db.execute(query).scalars().all()

    return ProductListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: UUID,
    db: Session = Depends(get_db),
):
    stmt = select(Product).where(Product.id == product_id)
    product = db.execute(stmt).scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return product
