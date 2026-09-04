import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    Text,
    Numeric,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.cart_item import CartItem
    from app.models.merchant import Merchant
    from app.models.order_item import OrderItem


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    inventory: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    attributes: Mapped[Dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"), default=dict, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("merchant_id", "sku", name="uq_products_merchant_sku"),
        CheckConstraint("price >= 0", name="chk_products_price_non_negative"),
        CheckConstraint("inventory >= 0", name="chk_products_inventory_non_negative"),
    )

    # Relationships
    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="products")
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="product"
    )
    cart_items: Mapped[List["CartItem"]] = relationship(
        "CartItem", back_populates="product"
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name}', sku='{self.sku}')>"
