import json
import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.core.seed import seed_catalog
from app.main import app
from app.models.order import Order
from app.models.payment import Payment
from app.models.product import Product
from app.services.razorpay_service import razorpay_service


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


def create_test_order_and_payment(client, customer_id: str):
    """Helper to create an order and initiate a payment order."""
    prod_res = client.get("/api/products")
    product = prod_res.json()["items"][0]

    # Add to cart
    client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": 1},
    )

    # Checkout order
    order_res = client.post("/api/orders", json={"customer_id": customer_id})
    assert order_res.status_code == 201
    order_data = order_res.json()

    # Initiate payment order
    pay_res = client.post(
        "/api/payments/create-order",
        json={"order_id": order_data["id"], "customer_id": customer_id},
    )
    assert pay_res.status_code == 200
    payment_data = pay_res.json()

    return order_data, payment_data


def test_valid_webhook_signature_and_payment_success():
    """1. Valid payment.captured event marks payment and order as paid."""
    client, engine = get_test_app_client()
    customer_id = str(uuid.uuid4())
    order, payment = create_test_order_and_payment(client, customer_id)

    rzp_order_id = payment["razorpay_order_id"]
    amount_in_paise = payment["amount_in_paise"]
    rzp_payment_id = f"pay_{uuid.uuid4().hex[:14]}"

    payload = {
        "entity": "event",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": rzp_payment_id,
                    "order_id": rzp_order_id,
                    "amount": amount_in_paise,
                    "currency": "INR",
                    "status": "captured",
                }
            }
        },
    }

    body_bytes = json.dumps(payload).encode("utf-8")
    signature = razorpay_service.generate_webhook_signature(body_bytes)

    res = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["order_status"] == "paid"
    assert data["payment_status"] == "paid"

    # Verify Database state
    with Session(engine) as session:
        db_order = session.query(Order).filter_by(id=uuid.UUID(order["id"])).first()
        assert db_order.status == "paid"

        db_payment = session.query(Payment).filter_by(id=uuid.UUID(payment["payment_id"])).first()
        assert db_payment.status == "paid"
        assert db_payment.razorpay_payment_id == rzp_payment_id


def test_invalid_webhook_signature_rejected():
    """2. Webhook with invalid signature is rejected with 400 Bad Request."""
    client, engine = get_test_app_client()
    customer_id = str(uuid.uuid4())
    order, payment = create_test_order_and_payment(client, customer_id)

    payload = {
        "entity": "event",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_fake_123",
                    "order_id": payment["razorpay_order_id"],
                    "amount": payment["amount_in_paise"],
                    "currency": "INR",
                }
            }
        },
    }

    body_bytes = json.dumps(payload).encode("utf-8")

    res = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": "invalid_hmac_signature_hex_12345",
        },
    )
    assert res.status_code == 400
    assert "invalid webhook signature" in res.json()["detail"].lower()

    # Order must remain pending_payment
    with Session(engine) as session:
        db_order = session.query(Order).filter_by(id=uuid.UUID(order["id"])).first()
        assert db_order.status == "pending_payment"


def test_missing_signature_rejected():
    """3. Webhook without signature header is rejected with 400 Bad Request."""
    client, _ = get_test_app_client()

    payload = {"entity": "event", "event": "payment.captured"}
    body_bytes = json.dumps(payload).encode("utf-8")

    res = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 400
    assert "missing x-razorpay-signature" in res.json()["detail"].lower()


def test_amount_mismatch_rejected():
    """4. Reject payment if webhook payload amount does not match authoritative order amount."""
    client, engine = get_test_app_client()
    customer_id = str(uuid.uuid4())
    order, payment = create_test_order_and_payment(client, customer_id)

    # Attempt amount tampering in webhook payload (e.g. 100 paise = ₹1 instead of real total)
    tampered_amount = 100

    payload = {
        "entity": "event",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_tampered_123",
                    "order_id": payment["razorpay_order_id"],
                    "amount": tampered_amount,
                    "currency": "INR",
                }
            }
        },
    }

    body_bytes = json.dumps(payload).encode("utf-8")
    signature = razorpay_service.generate_webhook_signature(body_bytes)

    res = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "error"
    assert "amount mismatch" in data["message"].lower()

    # Verify Order was NOT marked as paid
    with Session(engine) as session:
        db_order = session.query(Order).filter_by(id=uuid.UUID(order["id"])).first()
        assert db_order.status == "pending_payment"


def test_currency_mismatch_rejected():
    """5. Reject payment if webhook payload currency differs from order currency."""
    client, engine = get_test_app_client()
    customer_id = str(uuid.uuid4())
    order, payment = create_test_order_and_payment(client, customer_id)

    payload = {
        "entity": "event",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_cur_123",
                    "order_id": payment["razorpay_order_id"],
                    "amount": payment["amount_in_paise"],
                    "currency": "USD",  # Mismatched currency
                }
            }
        },
    }

    body_bytes = json.dumps(payload).encode("utf-8")
    signature = razorpay_service.generate_webhook_signature(body_bytes)

    res = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "error"
    assert "currency mismatch" in data["message"].lower()

    with Session(engine) as session:
        db_order = session.query(Order).filter_by(id=uuid.UUID(order["id"])).first()
        assert db_order.status == "pending_payment"


def test_unknown_razorpay_order_ignored():
    """6. Unknown Razorpay order ID returns 200 with ignored status."""
    client, _ = get_test_app_client()

    payload = {
        "entity": "event",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_unknown_123",
                    "order_id": "order_unknown_999999",
                    "amount": 500000,
                    "currency": "INR",
                }
            }
        },
    }

    body_bytes = json.dumps(payload).encode("utf-8")
    signature = razorpay_service.generate_webhook_signature(body_bytes)

    res = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ignored"


def test_duplicate_webhook_idempotency():
    """7. Duplicate webhook delivery is handled idempotently without error."""
    client, engine = get_test_app_client()
    customer_id = str(uuid.uuid4())
    order, payment = create_test_order_and_payment(client, customer_id)

    payload = {
        "entity": "event",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_idemp_123",
                    "order_id": payment["razorpay_order_id"],
                    "amount": payment["amount_in_paise"],
                    "currency": "INR",
                }
            }
        },
    }

    body_bytes = json.dumps(payload).encode("utf-8")
    signature = razorpay_service.generate_webhook_signature(body_bytes)

    # First webhook call -> marks paid
    res1 = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        },
    )
    assert res1.status_code == 200
    assert res1.json()["order_status"] == "paid"

    # Second webhook call -> idempotent acknowledgement
    res2 = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        },
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "ok"
    assert data2.get("idempotent") is True
    assert data2["order_status"] == "paid"


def test_payment_failed_event_handling():
    """8. payment.failed event marks payment record as failed without marking order paid."""
    client, engine = get_test_app_client()
    customer_id = str(uuid.uuid4())
    order, payment = create_test_order_and_payment(client, customer_id)

    rzp_payment_id = f"pay_failed_{uuid.uuid4().hex[:10]}"
    payload = {
        "entity": "event",
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": rzp_payment_id,
                    "order_id": payment["razorpay_order_id"],
                    "amount": payment["amount_in_paise"],
                    "currency": "INR",
                    "error_code": "BAD_REQUEST_ERROR",
                }
            }
        },
    }

    body_bytes = json.dumps(payload).encode("utf-8")
    signature = razorpay_service.generate_webhook_signature(body_bytes)

    res = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["payment_status"] == "failed"
    assert data["order_status"] == "pending_payment"

    with Session(engine) as session:
        db_payment = session.query(Payment).filter_by(id=uuid.UUID(payment["payment_id"])).first()
        assert db_payment.status == "failed"
        assert db_payment.razorpay_payment_id == rzp_payment_id

        db_order = session.query(Order).filter_by(id=uuid.UUID(order["id"])).first()
        assert db_order.status == "pending_payment"


def test_order_paid_event_handling():
    """9. order.paid event also reconciles and marks order as paid."""
    client, engine = get_test_app_client()
    customer_id = str(uuid.uuid4())
    order, payment = create_test_order_and_payment(client, customer_id)

    payload = {
        "entity": "event",
        "event": "order.paid",
        "payload": {
            "order": {
                "entity": {
                    "id": payment["razorpay_order_id"],
                    "amount": payment["amount_in_paise"],
                    "amount_paid": payment["amount_in_paise"],
                    "currency": "INR",
                    "status": "paid",
                }
            }
        },
    }

    body_bytes = json.dumps(payload).encode("utf-8")
    signature = razorpay_service.generate_webhook_signature(body_bytes)

    res = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        },
    )
    assert res.status_code == 200
    assert res.json()["order_status"] == "paid"

    with Session(engine) as session:
        db_order = session.query(Order).filter_by(id=uuid.UUID(order["id"])).first()
        assert db_order.status == "paid"


def test_malformed_json_body_rejected():
    """10. Malformed JSON payload is rejected with 400 Bad Request."""
    client, _ = get_test_app_client()

    body_bytes = b"not-a-valid-json-payload"
    signature = razorpay_service.generate_webhook_signature(body_bytes)

    res = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        },
    )
    assert res.status_code == 400
    assert "malformed json" in res.json()["detail"].lower()
