"""
Phase 17E — A2A Authentication Boundary Test Suite

Validates the strict cryptographic and architectural separation between:
1. Human/user authentication (Authorization: Bearer <JWT>)
2. Machine-to-machine Agent Commerce authentication (X-Agent-Key: <configured key>)
3. External Razorpay webhook authentication (X-Razorpay-Signature: HMAC-SHA256)

Requirements covered:
- valid X-Agent-Key -> Agent Commerce succeeds (200 / 201)
- missing X-Agent-Key -> 401 Unauthorized
- invalid X-Agent-Key -> 401 Unauthorized
- valid customer JWT without X-Agent-Key -> 401 Unauthorized
- valid admin JWT without X-Agent-Key -> 401 Unauthorized
- valid admin JWT with invalid X-Agent-Key -> 401 Unauthorized
- valid JWT still works on appropriate protected user endpoints (cart, dashboard, admin)
- X-Agent-Key cannot substitute for JWT on JWT-protected endpoints (cart, orders, dashboard, admin)
- Razorpay webhook authentication remains independent (HMAC verification required; neither JWT nor X-Agent-Key can substitute)
"""

import hashlib
import hmac
import json
import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.core.seed import seed_catalog
from app.main import app
from app.models.order import Order
from app.models.product import Product
from app.models.user import User, UserRole


def get_test_app_client():
    """Create test client with clean in-memory SQLite DB with seeded catalog."""
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


def create_user_with_role(engine, email: str, role: str = UserRole.CUSTOMER.value):
    """Helper to create a test user with a specific authoritative role in the database."""
    user_id = uuid.uuid4()
    with Session(engine) as session:
        user = User(
            id=user_id,
            email=email.lower().strip(),
            password_hash=hash_password("StrongPassword123!"),
            role=role,
            is_active=True,
        )
        session.add(user)
        session.commit()

    token = create_access_token(subject=str(user_id), additional_claims={"role": role})
    return user_id, token


def get_valid_agent_key():
    """Retrieve configured or default test agent key."""
    return settings.COMMERCE_AGENT_KEY or "ag_live_key_test_commerce_2026"


# ==============================================================================
# 1. Agent Commerce (X-Agent-Key) Isolation Tests
# ==============================================================================

def test_valid_agent_key_succeeds_on_agent_commerce():
    """1. Valid X-Agent-Key successfully accesses Agent Commerce endpoints."""
    client, engine = get_test_app_client()
    agent_key = get_valid_agent_key()
    headers = {"X-Agent-Key": agent_key}

    # Discover products
    res_disc = client.post(
        "/api/agent-commerce/discover",
        json={"query": "headphones"},
        headers=headers,
    )
    assert res_disc.status_code == 200
    assert "products" in res_disc.json()

    # Inventory check
    with Session(engine) as session:
        prod = session.query(Product).first()
        prod_id = str(prod.id)

    res_inv = client.post(
        "/api/agent-commerce/inventory/check",
        json={"product_id": prod_id, "quantity": 1},
        headers=headers,
    )
    assert res_inv.status_code == 200
    assert res_inv.json()["available"] is True


def test_missing_agent_key_returns_401():
    """2. Missing X-Agent-Key on Agent Commerce returns 401 Unauthorized."""
    client, engine = get_test_app_client()

    res_disc = client.post(
        "/api/agent-commerce/discover",
        json={"query": "headphones"},
    )
    assert res_disc.status_code == 401
    assert "X-Agent-Key header required" in res_disc.json()["detail"]


def test_invalid_agent_key_returns_401():
    """3. Invalid or forged X-Agent-Key on Agent Commerce returns 401 Unauthorized."""
    client, engine = get_test_app_client()
    headers = {"X-Agent-Key": "invalid_forged_agent_secret_key_9999"}

    res = client.post(
        "/api/agent-commerce/discover",
        json={"query": "headphones"},
        headers=headers,
    )
    assert res.status_code == 401
    assert "X-Agent-Key header required" in res.json()["detail"]


def test_valid_customer_jwt_without_agent_key_returns_401():
    """4. Valid customer User JWT cannot authenticate to Agent Commerce without X-Agent-Key."""
    client, engine = get_test_app_client()
    _, customer_token = create_user_with_role(engine, "shopper.boundary@example.com", role="customer")
    headers = {"Authorization": f"Bearer {customer_token}"}

    res = client.post(
        "/api/agent-commerce/discover",
        json={"query": "headphones"},
        headers=headers,
    )
    assert res.status_code == 401
    assert "X-Agent-Key header required" in res.json()["detail"]


def test_valid_admin_jwt_without_agent_key_returns_401():
    """5. Even a valid platform Admin JWT cannot authenticate to Agent Commerce without X-Agent-Key."""
    client, engine = get_test_app_client()
    _, admin_token = create_user_with_role(engine, "admin.boundary@example.com", role="admin")
    headers = {"Authorization": f"Bearer {admin_token}"}

    res = client.post(
        "/api/agent-commerce/discover",
        json={"query": "headphones"},
        headers=headers,
    )
    assert res.status_code == 401
    assert "X-Agent-Key header required" in res.json()["detail"]


def test_valid_admin_jwt_with_invalid_agent_key_returns_401():
    """6. Admin JWT provided alongside an invalid X-Agent-Key cannot bypass agent key validation."""
    client, engine = get_test_app_client()
    _, admin_token = create_user_with_role(engine, "admin.bypass@example.com", role="admin")
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "X-Agent-Key": "tampered_or_invalid_agent_key",
    }

    res = client.post(
        "/api/agent-commerce/discover",
        json={"query": "headphones"},
        headers=headers,
    )
    assert res.status_code == 401
    assert "X-Agent-Key header required" in res.json()["detail"]


# ==============================================================================
# 2. User Protected Endpoints Isolation (JWT required, X-Agent-Key cannot substitute)
# ==============================================================================

def test_valid_jwt_works_on_appropriate_protected_endpoints():
    """7. Valid user JWTs continue to work as intended on protected user endpoints."""
    client, engine = get_test_app_client()
    cust_id, cust_token = create_user_with_role(engine, "shopper.legit@example.com", role="customer")
    _, merch_token = create_user_with_role(engine, "store.owner@example.com", role="merchant")
    _, admin_token = create_user_with_role(engine, "platform.admin@example.com", role="admin")

    # Customer on cart
    res_cart = client.post(
        "/api/cart",
        json={"customer_id": str(cust_id)},
        headers={"Authorization": f"Bearer {cust_token}"},
    )
    assert res_cart.status_code == 200

    # Merchant on dashboard
    res_dash = client.get(
        "/api/dashboard/overview",
        headers={"Authorization": f"Bearer {merch_token}"},
    )
    assert res_dash.status_code == 200

    # Admin on admin system status
    res_admin = client.get(
        "/api/admin/system/status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin.status_code == 200


def test_agent_key_cannot_substitute_for_jwt_on_cart():
    """8. X-Agent-Key alone cannot authenticate to customer cart endpoint (401)."""
    client, engine = get_test_app_client()
    agent_key = get_valid_agent_key()
    headers = {"X-Agent-Key": agent_key}

    res = client.post("/api/cart", headers=headers)
    assert res.status_code == 401
    assert "Authorization" in res.json()["detail"]


def test_agent_key_cannot_substitute_for_jwt_on_orders():
    """9. X-Agent-Key alone cannot authenticate to customer order endpoint (401)."""
    client, engine = get_test_app_client()
    agent_key = get_valid_agent_key()
    headers = {"X-Agent-Key": agent_key}

    res = client.post(
        "/api/orders",
        json={"customer_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert res.status_code == 401
    assert "Authorization" in res.json()["detail"]


def test_agent_key_cannot_substitute_for_jwt_on_dashboard():
    """10. X-Agent-Key alone cannot authenticate to merchant dashboard (401)."""
    client, engine = get_test_app_client()
    agent_key = get_valid_agent_key()
    headers = {"X-Agent-Key": agent_key}

    res = client.get("/api/dashboard/overview", headers=headers)
    assert res.status_code == 401
    assert "Authorization" in res.json()["detail"]


def test_agent_key_cannot_substitute_for_jwt_on_admin():
    """11. X-Agent-Key alone cannot authenticate to platform admin endpoints (401)."""
    client, engine = get_test_app_client()
    agent_key = get_valid_agent_key()
    headers = {"X-Agent-Key": agent_key}

    res = client.get("/api/admin/system/status", headers=headers)
    assert res.status_code == 401
    assert "Authorization" in res.json()["detail"]


# ==============================================================================
# 3. Razorpay Webhook Independence Tests
# ==============================================================================

def test_razorpay_webhook_requires_hmac_and_rejects_jwt_or_agent_key():
    """12. Razorpay webhook uses HMAC signature; passing JWT or X-Agent-Key without HMAC fails (400)."""
    client, engine = get_test_app_client()
    agent_key = get_valid_agent_key()
    _, admin_token = create_user_with_role(engine, "admin.hook@example.com", role="admin")

    webhook_payload = json.dumps({"event": "payment.captured", "payload": {}})

    # 1. Webhook with no headers -> 400
    res_no_sig = client.post(
        "/api/payments/webhook",
        content=webhook_payload,
        headers={"Content-Type": "application/json"},
    )
    assert res_no_sig.status_code == 400
    assert "signature" in res_no_sig.json()["detail"].lower()

    # 2. Webhook with X-Agent-Key but no HMAC signature -> 400
    res_agent_key = client.post(
        "/api/payments/webhook",
        content=webhook_payload,
        headers={"Content-Type": "application/json", "X-Agent-Key": agent_key},
    )
    assert res_agent_key.status_code == 400
    assert "signature" in res_agent_key.json()["detail"].lower()

    # 3. Webhook with Admin JWT but no HMAC signature -> 400
    res_admin_jwt = client.post(
        "/api/payments/webhook",
        content=webhook_payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin_jwt.status_code == 400
    assert "signature" in res_admin_jwt.json()["detail"].lower()


def test_razorpay_webhook_succeeds_with_valid_hmac_signature():
    """13. Razorpay webhook succeeds when valid HMAC signature is present, irrespective of other headers."""
    client, engine = get_test_app_client()
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET or "rzp_webhook_secret_test_placeholder"
    cust_id, cust_token = create_user_with_role(engine, "hook.tester@example.com", role="customer")
    auth_headers = {"Authorization": f"Bearer {cust_token}"}

    # 1. Add item to cart
    with Session(engine) as session:
        prod = session.query(Product).first()
        prod_id = str(prod.id)

    client.post(
        f"/api/cart/{cust_id}/items",
        json={"product_id": prod_id, "quantity": 1},
        headers=auth_headers,
    )

    # 2. Checkout order
    order_res = client.post(
        "/api/orders",
        json={"customer_id": str(cust_id)},
        headers=auth_headers,
    )
    assert order_res.status_code == 201
    order_data = order_res.json()

    # 3. Initiate payment
    pay_res = client.post(
        "/api/payments/create-order",
        json={"order_id": order_data["id"], "customer_id": str(cust_id)},
        headers=auth_headers,
    )
    assert pay_res.status_code == 200
    payment_data = pay_res.json()
    rzp_order_id = payment_data["razorpay_order_id"]

    amount_in_paise = int(round(float(payment_data["amount"]) * 100))

    webhook_body = json.dumps({
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_capture_boundary",
                    "order_id": rzp_order_id,
                    "amount": amount_in_paise,
                    "currency": "INR",
                    "status": "captured",
                    "notes": {"internal_order_id": order_data["id"]},
                }
            }
        }
    })

    # Compute valid HMAC-SHA256 signature
    valid_sig = hmac.new(
        webhook_secret.encode("utf-8"),
        webhook_body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    res = client.post(
        "/api/payments/webhook",
        content=webhook_body,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": valid_sig,
        },
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
