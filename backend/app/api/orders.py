import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.order import (
    OrderCreateRequest,
    OrderListResponse,
    OrderResponse,
)
from app.services.order_service import order_service

router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create order from active cart",
)
def create_order(
    payload: OrderCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Creates a new Order by converting the customer's active cart.
    - Validates authoritative prices and inventory.
    - Captures historical price snapshots in OrderItems.
    - Marks cart as converted.
    - Initial order status is set to 'pending_payment'.
    """
    order = order_service.create_order_from_cart(
        db,
        customer_id=payload.customer_id,
        cart_id=payload.cart_id,
    )
    return order_service.format_order_response(order)


@router.get(
    "/{customer_id}",
    response_model=OrderListResponse,
    status_code=status.HTTP_200_OK,
    summary="List customer orders",
)
def list_customer_orders(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Retrieves all orders placed by the customer, sorted by creation date descending.
    """
    orders = order_service.get_customer_orders(db, customer_id=customer_id)
    return order_service.format_order_list_response(orders)


@router.get(
    "/{customer_id}/{order_id}",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single order details",
)
def get_order_detail(
    customer_id: uuid.UUID,
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Retrieves a specific order for the given customer. Returns 404 if not found or belongs to another customer.
    """
    order = order_service.get_customer_order_by_id(
        db, customer_id=customer_id, order_id=order_id
    )
    return order_service.format_order_response(order)
