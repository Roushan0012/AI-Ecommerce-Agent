import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.cart import (
    CartCreateRequest,
    CartItemCreateRequest,
    CartItemUpdateRequest,
    CartResponse,
)
from app.services.cart_service import cart_service

router = APIRouter(prefix="/api/cart", tags=["Cart"])


@router.post(
    "",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or retrieve active customer cart",
)
def create_or_get_cart(
    payload: Optional[CartCreateRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Creates a new cart or retrieves existing active cart for the customer.
    If no customer_id is provided, a new UUID is generated.
    """
    customer_id = payload.customer_id if payload else None
    cart = cart_service.get_or_create_active_cart(db, customer_id=customer_id)
    return cart_service.format_cart_response(cart)


@router.get(
    "/{customer_id}",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    summary="Get customer active cart",
)
def get_cart(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Retrieves the customer's active cart. Returns 404 if no active cart exists.
    """
    cart = cart_service.get_active_cart(db, customer_id=customer_id)
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active cart not found for this customer.",
        )
    return cart_service.format_cart_response(cart)


@router.post(
    "/{customer_id}/items",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    summary="Add product to cart",
)
def add_cart_item(
    customer_id: uuid.UUID,
    payload: CartItemCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Adds a product to customer's active cart.
    Price is fetched strictly server-side from products table.
    If product already exists in cart, increments quantity.
    """
    cart = cart_service.add_item_to_cart(
        db,
        customer_id=customer_id,
        product_id=payload.product_id,
        quantity=payload.quantity,
    )
    return cart_service.format_cart_response(cart)


@router.put(
    "/{customer_id}/items/{product_id}",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    summary="Update cart item quantity",
)
def update_cart_item(
    customer_id: uuid.UUID,
    product_id: uuid.UUID,
    payload: CartItemUpdateRequest,
    db: Session = Depends(get_db),
):
    """
    Updates the quantity for a product in customer's active cart.
    Validates inventory and recalculates line totals and cart totals.
    """
    cart = cart_service.update_item_quantity(
        db,
        customer_id=customer_id,
        product_id=product_id,
        quantity=payload.quantity,
    )
    return cart_service.format_cart_response(cart)


@router.delete(
    "/{customer_id}/items/{product_id}",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove product from cart",
)
def remove_cart_item(
    customer_id: uuid.UUID,
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Removes a product item from customer's active cart and recalculates totals.
    """
    cart = cart_service.remove_item_from_cart(
        db,
        customer_id=customer_id,
        product_id=product_id,
    )
    return cart_service.format_cart_response(cart)
