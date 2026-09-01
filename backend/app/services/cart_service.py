import uuid
from decimal import Decimal
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product import Product
from app.schemas.cart import CartItemResponse, CartResponse


class CartService:
    """Service handling authoritative cart creation, item management, and server-side pricing."""

    @classmethod
    def get_or_create_active_cart(
        cls, db: Session, customer_id: Optional[uuid.UUID] = None
    ) -> Cart:
        """Finds or creates an active cart for the customer."""
        if customer_id is None:
            customer_id = uuid.uuid4()

        stmt = (
            select(Cart)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
            .where(Cart.customer_id == customer_id, Cart.status == "active")
        )
        cart = db.execute(stmt).scalar_one_or_none()

        if not cart:
            cart = Cart(
                id=uuid.uuid4(),
                customer_id=customer_id,
                status="active",
                currency="INR",
                subtotal=Decimal("0.00"),
                discount=Decimal("0.00"),
                total=Decimal("0.00"),
            )
            db.add(cart)
            db.commit()
            db.refresh(cart)

        return cart

    @classmethod
    def get_active_cart(cls, db: Session, customer_id: uuid.UUID) -> Optional[Cart]:
        """Retrieves active cart for customer if present."""
        stmt = (
            select(Cart)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
            .where(Cart.customer_id == customer_id, Cart.status == "active")
        )
        return db.execute(stmt).scalar_one_or_none()

    @classmethod
    def add_item_to_cart(
        cls,
        db: Session,
        customer_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: int,
    ) -> Cart:
        """
        Adds a product to active cart with strict server-side price & inventory validation.
        """
        if quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be a positive integer.",
            )

        # 1. Authoritative Product Validation
        prod_stmt = select(Product).where(Product.id == product_id)
        product = db.execute(prod_stmt).scalar_one_or_none()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found.",
            )

        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product '{product.name}' is currently inactive.",
            )

        if product.inventory <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product '{product.name}' is out of stock.",
            )

        # 2. Get or create active cart
        cart = cls.get_or_create_active_cart(db, customer_id)

        # 3. Check for existing cart item
        item_stmt = select(CartItem).where(
            CartItem.cart_id == cart.id, CartItem.product_id == product_id
        )
        existing_item = db.execute(item_stmt).scalar_one_or_none()

        if existing_item:
            new_quantity = existing_item.quantity + quantity
            if new_quantity > product.inventory:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Requested total quantity ({new_quantity}) exceeds available inventory ({product.inventory}) for '{product.name}'.",
                )
            existing_item.quantity = new_quantity
            existing_item.unit_price = product.price
            existing_item.total_price = Decimal(str(new_quantity)) * product.price
        else:
            if quantity > product.inventory:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Requested quantity ({quantity}) exceeds available inventory ({product.inventory}) for '{product.name}'.",
                )
            new_item = CartItem(
                id=uuid.uuid4(),
                cart_id=cart.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=product.price,
                total_price=Decimal(str(quantity)) * product.price,
            )
            db.add(new_item)

        db.flush()

        # 4. Authoritative Subtotal & Total Recalculation
        cls.recalculate_cart_totals(db, cart)
        db.commit()

        return cls.get_or_create_active_cart(db, customer_id)

    @classmethod
    def update_item_quantity(
        cls,
        db: Session,
        customer_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: int,
    ) -> Cart:
        """Updates quantity for an existing cart item."""
        if quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be a positive integer. Use DELETE to remove item.",
            )

        cart = cls.get_active_cart(db, customer_id)
        if not cart:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active cart not found for this customer.",
            )

        item_stmt = select(CartItem).where(
            CartItem.cart_id == cart.id, CartItem.product_id == product_id
        )
        cart_item = db.execute(item_stmt).scalar_one_or_none()
        if not cart_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found in cart.",
            )

        # Revalidate authoritative product status & inventory
        prod_stmt = select(Product).where(Product.id == product_id)
        product = db.execute(prod_stmt).scalar_one_or_none()
        if not product or not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product is unavailable or inactive.",
            )

        if quantity > product.inventory:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Requested quantity ({quantity}) exceeds available inventory ({product.inventory}).",
            )

        cart_item.quantity = quantity
        cart_item.unit_price = product.price
        cart_item.total_price = Decimal(str(quantity)) * product.price

        db.flush()
        cls.recalculate_cart_totals(db, cart)
        db.commit()

        return cls.get_or_create_active_cart(db, customer_id)

    @classmethod
    def remove_item_from_cart(
        cls,
        db: Session,
        customer_id: uuid.UUID,
        product_id: uuid.UUID,
    ) -> Cart:
        """Removes a product from the active cart."""
        cart = cls.get_active_cart(db, customer_id)
        if not cart:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active cart not found for this customer.",
            )

        item_stmt = select(CartItem).where(
            CartItem.cart_id == cart.id, CartItem.product_id == product_id
        )
        cart_item = db.execute(item_stmt).scalar_one_or_none()
        if not cart_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found in cart.",
            )

        db.delete(cart_item)
        db.flush()

        cls.recalculate_cart_totals(db, cart)
        db.commit()

        return cls.get_or_create_active_cart(db, customer_id)

    @classmethod
    def recalculate_cart_totals(cls, db: Session, cart: Cart) -> None:
        """Server-side authoritative subtotal and total calculation."""
        items_stmt = (
            select(CartItem)
            .options(selectinload(CartItem.product))
            .where(CartItem.cart_id == cart.id)
        )
        items = db.execute(items_stmt).scalars().all()

        subtotal = Decimal("0.00")
        for it in items:
            # Re-read authoritative unit price from product
            unit_price = it.product.price if it.product else it.unit_price
            it.unit_price = unit_price
            it.total_price = Decimal(str(it.quantity)) * unit_price
            subtotal += it.total_price

        cart.subtotal = subtotal
        discount = cart.discount if cart.discount is not None else Decimal("0.00")
        cart.total = max(Decimal("0.00"), subtotal - discount)
        db.flush()

    @classmethod
    def format_cart_response(cls, cart: Cart) -> CartResponse:
        """Formats SQLAlchemy Cart model into response schema."""
        item_responses: List[CartItemResponse] = []
        total_quantity = 0

        for it in cart.items:
            total_quantity += it.quantity
            item_responses.append(
                CartItemResponse(
                    id=it.id,
                    cart_id=it.cart_id,
                    product_id=it.product_id,
                    product_name=it.product.name if it.product else "Unknown Product",
                    sku=it.product.sku if it.product else "N/A",
                    category=it.product.category if it.product else None,
                    quantity=it.quantity,
                    unit_price=it.unit_price,
                    total_price=it.total_price,
                    created_at=it.created_at,
                    updated_at=it.updated_at,
                )
            )

        return CartResponse(
            id=cart.id,
            customer_id=cart.customer_id,
            status=cart.status,
            currency=cart.currency,
            items=item_responses,
            item_count=total_quantity,
            subtotal=cart.subtotal,
            discount=cart.discount,
            total=cart.total,
            created_at=cart.created_at,
            updated_at=cart.updated_at,
        )


cart_service = CartService()
