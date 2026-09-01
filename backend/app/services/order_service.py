import uuid
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.schemas.order import OrderItemResponse, OrderListResponse, OrderResponse


class OrderService:
    """Authoritative order creation from active cart with atomic transaction and inventory validation."""

    @classmethod
    def create_order_from_cart(
        cls,
        db: Session,
        customer_id: uuid.UUID,
        cart_id: Optional[uuid.UUID] = None,
    ) -> Order:
        """
        Atomically converts customer's active cart into an Order:
        1. Validates active cart existence and non-empty items.
        2. Validates product status, authoritative price, and inventory for every item.
        3. Creates Order and OrderItem records with immutable price snapshots.
        4. Marks cart status as 'converted'.
        5. Atomic commit or rollback.
        """
        # 1. Locate active cart
        cart_stmt = (
            select(Cart)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
            .where(Cart.customer_id == customer_id)
        )
        if cart_id:
            cart_stmt = cart_stmt.where(Cart.id == cart_id)
        else:
            cart_stmt = cart_stmt.where(Cart.status == "active")

        cart = db.execute(cart_stmt).scalar_one_or_none()

        if not cart:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active cart not found for customer.",
            )

        if cart.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cart has already been {cart.status} and cannot be converted into an order.",
            )

        if not cart.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create an order from an empty cart. Please add products first.",
            )

        try:
            # 2. Revalidate all items against authoritative DB
            calculated_subtotal = Decimal("0.00")
            order_items_to_create: List[OrderItem] = []
            merchant_id: Optional[uuid.UUID] = None

            order_id = uuid.uuid4()

            for item in cart.items:
                prod_stmt = select(Product).where(Product.id == item.product_id)
                product = db.execute(prod_stmt).scalar_one_or_none()

                if not product:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Product with ID '{item.product_id}' is no longer available.",
                    )

                if not product.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Product '{product.name}' is inactive and cannot be purchased.",
                    )

                if item.quantity > product.inventory:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient inventory for '{product.name}'. Available: {product.inventory}, Requested: {item.quantity}.",
                    )

                merchant_id = product.merchant_id
                authoritative_unit_price = product.price
                line_total = Decimal(str(item.quantity)) * authoritative_unit_price
                calculated_subtotal += line_total

                # Create OrderItem with immutable product name and price snapshots
                order_item = OrderItem(
                    id=uuid.uuid4(),
                    order_id=order_id,
                    product_id=product.id,
                    product_name=product.name,
                    sku=product.sku,
                    quantity=item.quantity,
                    unit_price=authoritative_unit_price,
                    total_price=line_total,
                )
                order_items_to_create.append(order_item)

            if merchant_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot determine merchant for order items.",
                )

            # Calculate server-side discount and final total
            discount = cart.discount if cart.discount is not None else Decimal("0.00")
            final_total = max(Decimal("0.00"), calculated_subtotal - discount)

            # 3. Create Order
            order = Order(
                id=order_id,
                merchant_id=merchant_id,
                customer_id=customer_id,
                cart_id=cart.id,
                status="pending_payment",
                currency="INR",
                subtotal=calculated_subtotal,
                discount=discount,
                total=final_total,
            )
            db.add(order)

            for oi in order_items_to_create:
                db.add(oi)

            # 4. Mark Cart as Converted
            cart.status = "converted"

            db.commit()

            # Refresh order with items
            refresh_stmt = (
                select(Order)
                .options(selectinload(Order.items))
                .where(Order.id == order_id)
            )
            created_order = db.execute(refresh_stmt).scalar_one()
            return created_order

        except HTTPException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create order: {str(exc)}",
            )

    @classmethod
    def get_customer_orders(
        cls, db: Session, customer_id: uuid.UUID
    ) -> List[Order]:
        """Retrieves all orders placed by the customer."""
        stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
        )
        return list(db.execute(stmt).scalars().all())

    @classmethod
    def get_customer_order_by_id(
        cls, db: Session, customer_id: uuid.UUID, order_id: uuid.UUID
    ) -> Order:
        """Retrieves a single order belonging to customer, or raises 404."""
        stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id, Order.customer_id == customer_id)
        )
        order = db.execute(stmt).scalar_one_or_none()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found for this customer.",
            )
        return order

    @classmethod
    def format_order_response(cls, order: Order) -> OrderResponse:
        """Formats SQLAlchemy Order model into response schema."""
        item_responses: List[OrderItemResponse] = []
        for it in order.items:
            item_responses.append(
                OrderItemResponse(
                    id=it.id,
                    order_id=it.order_id,
                    product_id=it.product_id,
                    product_name=it.product_name,
                    sku=it.sku,
                    unit_price=it.unit_price,
                    quantity=it.quantity,
                    total_price=it.total_price,
                    created_at=it.created_at,
                )
            )

        return OrderResponse(
            id=order.id,
            merchant_id=order.merchant_id,
            customer_id=order.customer_id,
            cart_id=order.cart_id,
            status=order.status,
            currency=order.currency,
            subtotal=order.subtotal,
            discount=order.discount,
            total=order.total,
            items=item_responses,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    @classmethod
    def format_order_list_response(cls, orders: List[Order]) -> OrderListResponse:
        """Formats a list of orders into response schema."""
        return OrderListResponse(
            items=[cls.format_order_response(o) for o in orders],
            total=len(orders),
        )


order_service = OrderService()
