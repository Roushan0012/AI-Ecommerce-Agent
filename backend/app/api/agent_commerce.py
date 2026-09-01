import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.agent_commerce import (
    AgentCartItemRequest,
    AgentDiscoveryRequest,
    AgentDiscoveryResponse,
    AgentInventoryCheckRequest,
    AgentInventoryCheckResponse,
    AgentOrderCreateRequest,
    AgentPaymentInitiateRequest,
    AgentProductDetailResponse,
)
from app.schemas.cart import CartCreateRequest, CartResponse
from app.schemas.order import OrderResponse
from app.schemas.payment import PaymentOrderResponse
from app.services.agent_commerce_service import (
    agent_commerce_service,
    verify_agent_api_key,
)
from app.services.cart_service import cart_service

router = APIRouter(
    prefix="/api/agent-commerce",
    tags=["Agent-to-Agent Commerce"],
    dependencies=[Depends(verify_agent_api_key)],
)


@router.post(
    "/discover",
    response_model=AgentDiscoveryResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover Catalog Products for Buyer Agent",
)
async def discover_products(
    request: AgentDiscoveryRequest,
    db: Session = Depends(get_db),
):
    """
    Translates buyer agent's natural shopping query into structured catalog filters
    and returns matching products from the authoritative catalog.
    """
    return await agent_commerce_service.discover_products(db=db, request=request)


@router.get(
    "/products/{product_id}",
    response_model=AgentProductDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Authoritative Product Details",
)
def get_product_details(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Returns authoritative product specifications, live stock status, and server-side pricing.
    """
    return agent_commerce_service.get_product_details(db=db, product_id=product_id)


@router.post(
    "/inventory/check",
    response_model=AgentInventoryCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Inventory Availability",
)
def check_inventory(
    request: AgentInventoryCheckRequest,
    db: Session = Depends(get_db),
):
    """
    Validates product availability and quantity bounds before initiating checkout.
    """
    return agent_commerce_service.check_inventory(
        db=db, product_id=request.product_id, quantity=request.quantity
    )


@router.post(
    "/cart",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    summary="Initialize or Retrieve Agent Cart",
)
def get_or_create_cart(
    request: CartCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Creates or retrieves active commerce cart for the given customer/session UUID.
    """
    cart = cart_service.get_or_create_active_cart(db=db, customer_id=request.customer_id)
    return cart_service.format_cart_response(cart)


@router.post(
    "/cart/items",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    summary="Add Product to Agent Cart",
)
def add_to_cart(
    request: AgentCartItemRequest,
    db: Session = Depends(get_db),
):
    """
    Adds product to active cart with server-calculated unit price and total price.
    """
    return agent_commerce_service.add_to_cart(db=db, request=request)


@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Order from Cart (Idempotent)",
)
def create_order(
    request: AgentOrderCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Converts active cart into an authoritative order with revalidated inventory.
    Repeated calls with the same cart return the existing created order.
    """
    return agent_commerce_service.create_order(db=db, request=request)


@router.post(
    "/payments/initiate",
    response_model=PaymentOrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Initiate Razorpay Test Payment Order",
)
def initiate_payment(
    request: AgentPaymentInitiateRequest,
    db: Session = Depends(get_db),
):
    """
    Initiates payment order with Razorpay test mode using backend-authoritative amount.
    """
    return agent_commerce_service.initiate_payment(db=db, request=request)
