import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, require_customer
from app.models.user import User
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
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Creates a new Order by converting the authenticated customer's active cart.
    Enforces ownership and server-authoritative pricing and inventory constraints.
    """
    if payload.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create order for another user.",
        )
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
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Retrieves all orders placed by the authenticated customer.
    Enforces ownership.
    """
    if customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to these orders.",
        )
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
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Retrieves a specific order for the authenticated customer.
    Enforces ownership.
    """
    if customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this order.",
        )
    order = order_service.get_customer_order_by_id(
        db, customer_id=customer_id, order_id=order_id
    )
    return order_service.format_order_response(order)
