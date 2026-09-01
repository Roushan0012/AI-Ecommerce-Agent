import uuid
from decimal import Decimal
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.core.seed import seed_catalog
from app.main import app
from app.models.cart import Cart
from app.models.merchant import Merchant
from app.models.order import Order
from app.models.payment import Payment
from app.models.product import Product


def get_test_app_client():
    """Create test client with in-memory SQLite database seeded with catalog data."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        seed_catalog(session)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client, engine


def create_test_order(client, customer_id: str) -> dict:
    """Helper to create a valid application order."""
    # Get product
    prod_res = client.get("/api/products")
    product = prod_res.json()["items"][0]

    # Add to cart
    client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": 2},
    )

    # Checkout order
    order_res = client.post("/api/orders", json={"customer_id": customer_id})
    assert order_res.status_code == 201
    return order_res.json()


def test_create_payment_order_success():
    """1. Valid order creates Razorpay order with authoritative amount and paise conversion."""
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    order = create_test_order(client, customer_id)

    order_id = order["id"]
    order_total = float(order["total"])
    expected_paise = int(round(order_total * 100))

    res = client.post(
        "/api/payments/create-order",
        json={"order_id": order_id, "customer_id": customer_id},
    )
    assert res.status_code == 200
    data = res.json()

    assert "payment_id" in data
    assert data["order_id"] == order_id
    assert "razorpay_order_id" in data
    assert data["razorpay_order_id"].startswith("order_")
    assert float(data["amount"]) == order_total
    assert data["amount_in_paise"] == expected_paise
    assert data["currency"] == "INR"
    assert "key_id" in data
    assert data["status"] == "created"


def test_create_payment_order_nonexistent_order():
    """2. Nonexistent order returns 404 Not Found."""
    client, _ = get_test_app_client()
    fake_order_id = str(uuid.uuid4())

    res = client.post(
        "/api/payments/create-order",
        json={"order_id": fake_order_id},
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_create_payment_order_ineligible_paid_order():
    """3. Reject payment creation for an already paid order."""
    client, engine = get_test_app_client()
    customer_id = str(uuid.uuid4())
    order = create_test_order(client, customer_id)

    # Set status to paid in DB
    with Session(engine) as session:
        db_order = session.query(Order).filter_by(id=uuid.UUID(order["id"])).first()
        db_order.status = "paid"
        session.commit()

    res = client.post(
        "/api/payments/create-order",
        json={"order_id": order["id"]},
    )
    assert res.status_code == 400
    assert "already paid" in res.json()["detail"].lower()


def test_create_payment_order_ineligible_cancelled_order():
    """4. Reject payment creation for a cancelled order."""
    client, engine = get_test_app_client()
    customer_id = str(uuid.uuid4())
    order = create_test_order(client, customer_id)

    # Set status to cancelled in DB
    with Session(engine) as session:
        db_order = session.query(Order).filter_by(id=uuid.UUID(order["id"])).first()
        db_order.status = "cancelled"
        session.commit()

    res = client.post(
        "/api/payments/create-order",
        json={"order_id": order["id"]},
    )
    assert res.status_code == 400
    assert "cancelled" in res.json()["detail"].lower()


def test_client_cannot_tamper_payment_amount():
    """5. Server ignores any client-supplied amount or total parameters."""
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    order = create_test_order(client, customer_id)

    order_id = order["id"]
    real_total = float(order["total"])
    real_paise = int(round(real_total * 100))

    # Attempt malicious request with amount = 1.00
    res = client.post(
        "/api/payments/create-order",
        json={
            "order_id": order_id,
            "amount": 1.00,
            "amount_in_paise": 100,
            "total": 1.00,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert float(data["amount"]) == real_total
    assert data["amount_in_paise"] == real_paise


def test_razorpay_service_failure_handling():
    """6. Handle Razorpay API failure gracefully with 502 error."""
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    order = create_test_order(client, customer_id)

    with patch("app.services.payment_service.razorpay_service.create_razorpay_order", side_effect=Exception("Gateway Timeout")):
        with pytest.raises(Exception):
            client.post(
                "/api/payments/create-order",
                json={"order_id": order["id"]},
            )


def test_payment_record_persisted_in_db():
    """7. Verify Payment record and Order.razorpay_order_id are saved in database."""
    client, engine = get_test_app_client()
    customer_id = str(uuid.uuid4())
    order = create_test_order(client, customer_id)

    res = client.post(
        "/api/payments/create-order",
        json={"order_id": order["id"]},
    )
    assert res.status_code == 200
    data = res.json()
    rzp_order_id = data["razorpay_order_id"]
    payment_id = data["payment_id"]

    with Session(engine) as session:
        # Check Payment row
        payment = session.query(Payment).filter_by(id=uuid.UUID(payment_id)).first()
        assert payment is not None
        assert payment.order_id == uuid.UUID(order["id"])
        assert payment.razorpay_order_id == rzp_order_id
        assert payment.status == "created"
        assert float(payment.amount) == float(order["total"])

        # Check Order row
        db_order = session.query(Order).filter_by(id=uuid.UUID(order["id"])).first()
        assert db_order.razorpay_order_id == rzp_order_id


def test_payment_order_customer_mismatch():
    """8. Reject payment order creation if customer_id does not own the order."""
    client, _ = get_test_app_client()
    customer_a = str(uuid.uuid4())
    customer_b = str(uuid.uuid4())
    order = create_test_order(client, customer_a)

    # Customer B attempts to create payment for Customer A's order
    res = client.post(
        "/api/payments/create-order",
        json={"order_id": order["id"], "customer_id": customer_b},
    )
    assert res.status_code == 404
    assert "not found for this customer" in res.json()["detail"].lower()
