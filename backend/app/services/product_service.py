from decimal import Decimal
from typing import Optional
from uuid import UUID
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.models import Product
from app.schemas.product import ProductListResponse, ProductResponse


class ProductService:
    """Service handling catalog product queries and retrieval."""

    @staticmethod
    def list_products(
        db: Session,
        search: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        available: Optional[bool] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> ProductListResponse:
        filters = []

        # Availability / active filter
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

        # Keyword search filter (case-insensitive in name or description)
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

        # Count total matching products
        count_query = select(func.count(Product.id)).where(*filters)
        total = db.execute(count_query).scalar() or 0

        # Query products with deterministic ordering
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
            items=[ProductResponse.model_validate(p) for p in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    @staticmethod
    def get_product_by_id(db: Session, product_id: UUID) -> Optional[Product]:
        stmt = select(Product).where(Product.id == product_id)
        return db.execute(stmt).scalar_one_or_none()


product_service = ProductService()
