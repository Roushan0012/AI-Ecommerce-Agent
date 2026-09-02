"""
Phase 17F — Final Security & Regression Validation Test Suite

Validates the full hardening requirements for Phase 17:
1. JWT Security Validation (missing, malformed, non-Bearer, expired, wrong signature, invalid sub, nonexistent, inactive)
2. Authorization Security (customer/merchant/admin role boundaries, cross-user ownership, privilege escalation prevention)
3. A2A Authentication Isolation (X-Agent-Key vs JWT decoupling, mutual exclusion)
4. Payment Security (ownership enforcement, client amount tampering discarded, webhook HMAC verification & idempotency)
5. Password & Authentication Security (Argon2id hashing, no plaintext/hash leak, generic error messages, stateless tokens)
"""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.core.seed import seed_catalog
from app.main import app
from app.models.cart import Cart
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


def create_user_with_role(engine, email: str, role: str = UserRole.CUSTOMER.value, is_active: bool = True):
    """Helper to create a test user with a specific authoritative role in the database."""
    user_id = uuid.uuid4()
    raw_password = "SecurePassword123!"
    with Session(engine) as session:
        user = User(
            id=user_id,
            email=email.lower().strip(),
            password_hash=hash_password(raw_password),
            role=role,
            is_active=is_active,
        )
        session.add(user)
        session.commit()

    token = create_access_token(subject=str(user_id), additional_claims={"role": role})
    return user_id, token, raw_password


def get_valid_agent_key():
    """Retrieve configured or default test agent key."""
    return settings.COMMERCE_AGENT_KEY or "ag_live_key_test_commerce_2026"


# ==============================================================================
# 1. JWT Security Validation
# ==============================================================================

def test_missing_jwt_returns_401():
    """1.1 Missing Authorization header on protected endpoint returns 401."""
    client, _ = get_test_app_client()
    res = client.post("/api/cart")
    assert res.status_code == 401
    assert "Missing Authorization header" in res.json()["detail"]


def test_malformed_authorization_header_returns_401():
    """1.2 Malformed Authorization header returns 401."""
    client, _ = get_test_app_client()
    res = client.post("/api/cart", headers={"Authorization": "BearerTokenNoSpace"})
    assert res.status_code == 401
    assert "Bearer token required" in res.json()["detail"]


def test_non_bearer_authorization_returns_401():
    """1.3 Non-Bearer authorization scheme returns 401."""
    client, _ = get_test_app_client()
    res = client.post("/api/cart", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert res.status_code == 401
    assert "Invalid authentication scheme" in res.json()["detail"]


def test_malformed_jwt_token_returns_401():
    """1.4 Malformed JWT token string returns 401."""
    client, _ = get_test_app_client()
    res = client.post("/api/cart", headers={"Authorization": "Bearer invalid.jwt.format.string"})
    assert res.status_code == 401
    assert "Invalid access token" in res.json()["detail"]


def test_expired_jwt_token_returns_401():
    """1.5 Expired JWT token returns 401."""
    client, engine = get_test_app_client()
    user_id, _, _ = create_user_with_role(engine, "expired.user@example.com")

    # Manually craft token with expiration in the past
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": str(user_id),
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    res = client.post("/api/cart", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert "Token has expired" in res.json()["detail"]


def test_wrong_jwt_signature_returns_401():
    """1.6 JWT signed with incorrect secret key returns 401."""
    client, engine = get_test_app_client()
    user_id, _, _ = create_user_with_role(engine, "wrong.sig@example.com")

    # Sign with foreign/wrong key
    wrong_token = jwt.encode(
        {"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "completely_different_secret_key_1234567890",
        algorithm="HS256",
    )

    res = client.post("/api/cart", headers={"Authorization": f"Bearer {wrong_token}"})
    assert res.status_code == 401
    assert "Invalid access token" in res.json()["detail"]


def test_invalid_jwt_subject_returns_401():
    """1.7 JWT with non-UUID subject identifier returns 401."""
    client, _ = get_test_app_client()
    invalid_sub_token = jwt.encode(
        {"sub": "not-a-valid-uuid", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    res = client.post("/api/cart", headers={"Authorization": f"Bearer {invalid_sub_token}"})
    assert res.status_code == 401
    assert "Invalid access token" in res.json()["detail"]


def test_nonexistent_user_referenced_by_jwt_returns_401():
    """1.8 Valid JWT referencing a nonexistent user UUID in database returns 401."""
    client, _ = get_test_app_client()
    nonexistent_id = str(uuid.uuid4())
    token = create_access_token(subject=nonexistent_id)

    res = client.post("/api/cart", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert "User not found" in res.json()["detail"]


def test_inactive_user_referenced_by_jwt_returns_401():
    """1.9 Valid JWT referencing an inactive user (is_active=False) returns 401."""
    client, engine = get_test_app_client()
    _, token, _ = create_user_with_role(engine, "inactive.user@example.com", is_active=False)

    res = client.post("/api/cart", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert "User account is inactive" in res.json()["detail"]


def test_valid_jwt_succeeds_on_protected_endpoints():
    """1.10 Valid active JWT succeeds on authorized endpoints."""
    client, engine = get_test_app_client()
    user_id, token, _ = create_user_with_role(engine, "active.user@example.com")

    res = client.post("/api/cart", json={"customer_id": str(user_id)}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["customer_id"] == str(user_id)


def test_error_responses_do_not_leak_internal_secrets_or_stack_traces():
    """1.11 Error responses contain only sanitized detail and no internal traces or secrets."""
    client, _ = get_test_app_client()
    res = client.post("/api/cart", headers={"Authorization": "Bearer bad.token"})
    assert res.status_code == 401
    data = res.json()
    assert "detail" in data
    # Ensure no python trace, env vars, or secrets leaked
    assert "traceback" not in json.dumps(data).lower()
    assert "secret" not in json.dumps(data).lower()


# ==============================================================================
# 2. Authorization Security
# ==============================================================================

def test_customer_cannot_access_merchant_only_apis():
    """2.1 Customer role accessing merchant dashboard receives 403 Forbidden."""
    client, engine = get_test_app_client()
    _, customer_token, _ = create_user_with_role(engine, "cust.shield@example.com", role="customer")
    headers = {"Authorization": f"Bearer {customer_token}"}

    for path in ["/api/dashboard/overview", "/api/dashboard/orders", "/api/dashboard/activity"]:
        res = client.get(path, headers=headers)
        assert res.status_code == 403
        assert "forbidden" in res.json()["detail"].lower()


def test_customer_cannot_access_admin_only_apis():
    """2.2 Customer role accessing admin APIs receives 403 Forbidden."""
    client, engine = get_test_app_client()
    _, customer_token, _ = create_user_with_role(engine, "cust.shield2@example.com", role="customer")
    headers = {"Authorization": f"Bearer {customer_token}"}

    for path in ["/api/admin/system/status", "/api/admin/audit-logs", "/api/audit/admin/all"]:
        res = client.get(path, headers=headers)
        assert res.status_code == 403


def test_merchant_cannot_access_admin_only_apis():
    """2.3 Merchant role accessing admin APIs receives 403 Forbidden."""
    client, engine = get_test_app_client()
    _, merchant_token, _ = create_user_with_role(engine, "merch.shield@example.com", role="merchant")
    headers = {"Authorization": f"Bearer {merchant_token}"}

    for path in ["/api/admin/system/status", "/api/admin/audit-logs", "/api/audit/admin/all"]:
        res = client.get(path, headers=headers)
        assert res.status_code == 403


def test_authorized_merchant_access_succeeds():
    """2.4 Authorized merchant successfully accesses merchant dashboard."""
    client, engine = get_test_app_client()
    _, merchant_token, _ = create_user_with_role(engine, "merch.legit@example.com", role="merchant")
    headers = {"Authorization": f"Bearer {merchant_token}"}

    res = client.get("/api/dashboard/overview", headers=headers)
    assert res.status_code == 200
    assert "total_revenue" in res.json()


def test_authorized_admin_access_succeeds():
    """2.5 Authorized admin successfully accesses admin system status."""
    client, engine = get_test_app_client()
    _, admin_token, _ = create_user_with_role(engine, "admin.legit@example.com", role="admin")
    headers = {"Authorization": f"Bearer {admin_token}"}

    res = client.get("/api/admin/system/status", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_cross_user_private_resource_access_is_blocked():
    """2.6 Customer A cannot access Customer B's cart, orders, or audit trail."""
    client, engine = get_test_app_client()
    user_a_id, token_a, _ = create_user_with_role(engine, "user.a.idor@example.com", role="customer")
    user_b_id, _, _ = create_user_with_role(engine, "user.b.idor@example.com", role="customer")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Cross-cart read
    res_cart = client.get(f"/api/cart/{user_b_id}", headers=headers_a)
    assert res_cart.status_code == 403

    # Cross-order read
    res_orders = client.get(f"/api/orders/{user_b_id}", headers=headers_a)
    assert res_orders.status_code == 403

    # Cross-audit read
    res_audit = client.get(f"/api/audit/{user_b_id}", headers=headers_a)
    assert res_audit.status_code == 403


def test_client_supplied_id_cannot_override_jwt_identity():
    """2.7 Client-supplied customer_id in request body cannot override JWT identity."""
    client, engine = get_test_app_client()
    user_a_id, token_a, _ = create_user_with_role(engine, "spoof.a@example.com", role="customer")
    user_b_id, _, _ = create_user_with_role(engine, "spoof.b@example.com", role="customer")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    res = client.post(
        "/api/cart",
        json={"customer_id": str(user_b_id)},
        headers=headers_a,
    )
    assert res.status_code == 403
    assert "another user" in res.json()["detail"].lower()


def test_client_supplied_role_cannot_elevate_privileges():
    """2.8 Registration or payload with role='admin' cannot elevate privileges."""
    client, engine = get_test_app_client()

    # Registration attempt
    res = client.post(
        "/api/auth/register",
        json={"email": "hacker.wannabe@example.com", "password": "SecurePassword123!", "role": "admin"},
    )
    assert res.status_code == 201
    assert res.json()["role"] == "customer"

    # Database check
    with Session(engine) as session:
        user = session.query(User).filter(User.email == "hacker.wannabe@example.com").one()
        assert user.role == "customer"


def test_users_cannot_modify_their_own_role():
    """2.9 No API allows users to modify their own role; server DB is authoritative."""
    client, engine = get_test_app_client()
    user_id, token, _ = create_user_with_role(engine, "role.tamper@example.com", role="customer")
    headers = {"Authorization": f"Bearer {token}"}

    # Pass manipulated role into cart
    res = client.post(
        "/api/cart",
        json={"customer_id": str(user_id), "role": "admin"},
        headers=headers,
    )
    assert res.status_code == 200

    # DB record remains customer
    with Session(engine) as session:
        user = session.query(User).filter(User.id == user_id).one()
        assert user.role == "customer"


# ==============================================================================
# 3. A2A Authentication Isolation
# ==============================================================================

def test_valid_agent_key_agent_commerce_succeeds():
    """3.1 Valid X-Agent-Key succeeds on Agent Commerce."""
    client, _ = get_test_app_client()
    agent_key = get_valid_agent_key()
    res = client.post("/api/agent-commerce/discover", json={"query": "headphones"}, headers={"X-Agent-Key": agent_key})
    assert res.status_code == 200


def test_missing_agent_key_returns_401():
    """3.2 Missing X-Agent-Key on Agent Commerce returns 401."""
    client, _ = get_test_app_client()
    res = client.post("/api/agent-commerce/discover", json={"query": "headphones"})
    assert res.status_code == 401


def test_invalid_agent_key_returns_401():
    """3.3 Invalid X-Agent-Key on Agent Commerce returns 401."""
    client, _ = get_test_app_client()
    res = client.post("/api/agent-commerce/discover", json={"query": "headphones"}, headers={"X-Agent-Key": "bad_key"})
    assert res.status_code == 401


def test_user_jwt_cannot_authenticate_agent_commerce():
    """3.4 Valid customer User JWT without X-Agent-Key returns 401 on Agent Commerce."""
    client, engine = get_test_app_client()
    _, token, _ = create_user_with_role(engine, "a2a.probe@example.com", role="customer")
    res = client.post("/api/agent-commerce/discover", json={"query": "headphones"}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert "X-Agent-Key header required" in res.json()["detail"]


def test_admin_jwt_cannot_authenticate_agent_commerce():
    """3.5 Valid admin User JWT without X-Agent-Key returns 401 on Agent Commerce."""
    client, engine = get_test_app_client()
    _, admin_token, _ = create_user_with_role(engine, "a2a.admin.probe@example.com", role="admin")
    res = client.post("/api/agent-commerce/discover", json={"query": "headphones"}, headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 401
    assert "X-Agent-Key header required" in res.json()["detail"]


def test_agent_key_cannot_substitute_for_jwt_on_user_endpoints():
    """3.6 X-Agent-Key cannot substitute for JWT on user endpoints (cart, orders, dashboard, admin)."""
    client, _ = get_test_app_client()
    agent_key = get_valid_agent_key()
    headers = {"X-Agent-Key": agent_key}

    assert client.post("/api/cart", headers=headers).status_code == 401
    assert client.get("/api/dashboard/overview", headers=headers).status_code == 401
    assert client.get("/api/admin/system/status", headers=headers).status_code == 401


# ==============================================================================
# 4. Payment Security
# ==============================================================================

def test_payment_creation_enforces_order_ownership():
    """4.1 User A cannot create a payment order for User B's order."""
    client, engine = get_test_app_client()
    user_a_id, token_a, _ = create_user_with_role(engine, "pay.a@example.com", role="customer")
    user_b_id, token_b, _ = create_user_with_role(engine, "pay.b@example.com", role="customer")

    with Session(engine) as session:
        prod = session.query(Product).first()
        prod_id = str(prod.id)

    # User B creates order
    client.post(f"/api/cart/{user_b_id}/items", json={"product_id": prod_id, "quantity": 1}, headers={"Authorization": f"Bearer {token_b}"})
    order_b = client.post("/api/orders", json={"customer_id": str(user_b_id)}, headers={"Authorization": f"Bearer {token_b}"}).json()

    # User A tries to pay for User B's order
    res_pay = client.post(
        "/api/payments/create-order",
        json={"order_id": order_b["id"], "customer_id": str(user_a_id)},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_pay.status_code in [403, 404]
    assert "not found" in res_pay.json()["detail"].lower() or "forbidden" in res_pay.json()["detail"].lower()


def test_client_cannot_tamper_with_payment_amount():
    """4.2 Payment amount is server-authoritative; client cannot specify lower payment amount."""
    client, engine = get_test_app_client()
    user_id, token, _ = create_user_with_role(engine, "tamper.pay@example.com", role="customer")
    auth_headers = {"Authorization": f"Bearer {token}"}

    with Session(engine) as session:
        prod = session.query(Product).first()
        prod_id = str(prod.id)
        authoritative_price = prod.price

    client.post(f"/api/cart/{user_id}/items", json={"product_id": prod_id, "quantity": 1}, headers=auth_headers)
    order = client.post("/api/orders", json={"customer_id": str(user_id)}, headers=auth_headers).json()

    # Client tries to pass amount: 0.01
    pay_res = client.post(
        "/api/payments/create-order",
        json={"order_id": order["id"], "customer_id": str(user_id), "amount": "0.01"},
        headers=auth_headers,
    )
    assert pay_res.status_code == 200
    # Returned amount matches authoritative order total, NOT client 0.01
    assert Decimal(str(pay_res.json()["amount"])) == Decimal(str(order["total"]))


def test_razorpay_webhook_requires_valid_signature():
    """4.3 Webhook rejects requests with missing or invalid signature."""
    client, _ = get_test_app_client()

    # Missing signature -> 400
    res_missing = client.post("/api/payments/webhook", content="{}", headers={"Content-Type": "application/json"})
    assert res_missing.status_code == 400

    # Invalid signature -> 400
    res_invalid = client.post(
        "/api/payments/webhook",
        content="{}",
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": "invalid_sig_hex"},
    )
    assert res_invalid.status_code == 400


def test_razorpay_webhook_accepts_valid_signature_and_is_idempotent():
    """4.4 Valid webhook signature processes payment, and replay is idempotent."""
    client, engine = get_test_app_client()
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET or "rzp_webhook_secret_test_placeholder"
    cust_id, cust_token, _ = create_user_with_role(engine, "hook.idemp@example.com", role="customer")
    auth_headers = {"Authorization": f"Bearer {cust_token}"}

    with Session(engine) as session:
        prod = session.query(Product).first()
        prod_id = str(prod.id)

    client.post(f"/api/cart/{cust_id}/items", json={"product_id": prod_id, "quantity": 1}, headers=auth_headers)
    order_data = client.post("/api/orders", json={"customer_id": str(cust_id)}, headers=auth_headers).json()
    pay_data = client.post("/api/payments/create-order", json={"order_id": order_data["id"], "customer_id": str(cust_id)}, headers=auth_headers).json()

    rzp_order_id = pay_data["razorpay_order_id"]
    amount_in_paise = int(round(float(pay_data["amount"]) * 100))

    webhook_body = json.dumps({
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_idempotent_capture",
                    "order_id": rzp_order_id,
                    "amount": amount_in_paise,
                    "currency": "INR",
                    "status": "captured",
                    "notes": {"internal_order_id": order_data["id"]},
                }
            }
        }
    })

    valid_sig = hmac.new(webhook_secret.encode("utf-8"), webhook_body.encode("utf-8"), hashlib.sha256).hexdigest()
    headers = {"Content-Type": "application/json", "X-Razorpay-Signature": valid_sig}

    # 1. First event -> 200 OK
    res1 = client.post("/api/payments/webhook", content=webhook_body, headers=headers)
    assert res1.status_code == 200
    assert res1.json()["status"] == "ok"

    # 2. Replay duplicate event -> 200 OK with idempotent=True
    res2 = client.post("/api/payments/webhook", content=webhook_body, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["idempotent"] is True


# ==============================================================================
# 5. Password & Authentication Security
# ==============================================================================

def test_plaintext_passwords_never_stored_in_database():
    """5.1 Passwords in database are hashed with Argon2id; plaintext is never stored."""
    _, engine = get_test_app_client()
    user_id, _, raw_password = create_user_with_role(engine, "argon2.verify@example.com")

    with Session(engine) as session:
        user = session.query(User).filter(User.id == user_id).one()
        assert raw_password not in user.password_hash
        assert user.password_hash.startswith("$argon2id$")
        assert verify_password(raw_password, user.password_hash) is True
        assert verify_password("WrongPassword123!", user.password_hash) is False


def test_password_hashes_never_returned_in_api_responses():
    """5.2 User registration and login responses never return password_hash or secret keys."""
    client, _ = get_test_app_client()
    res_reg = client.post("/api/auth/register", json={"email": "no.hash.leak@example.com", "password": "SecurePassword123!"})
    assert res_reg.status_code == 201
    reg_data = res_reg.json()
    assert "password_hash" not in reg_data
    assert "password" not in reg_data

    res_login = client.post("/api/auth/login", json={"email": "no.hash.leak@example.com", "password": "SecurePassword123!"})
    assert res_login.status_code == 200
    login_data = res_login.json()
    assert "password_hash" not in login_data
    assert "password" not in login_data


def test_wrong_password_and_unknown_user_fail_with_identical_generic_error():
    """5.3 Wrong password and unknown user both return 401 with identical generic error."""
    client, engine = get_test_app_client()
    _, _, _ = create_user_with_role(engine, "known.user@example.com")

    # Wrong password for existing user
    res_wrong_pw = client.post("/api/auth/login", json={"email": "known.user@example.com", "password": "WrongPassword!"})
    assert res_wrong_pw.status_code == 401
    assert res_wrong_pw.json()["detail"] == "Invalid email or password."

    # Unknown user
    res_unknown = client.post("/api/auth/login", json={"email": "unknown.user.random@example.com", "password": "AnyPassword!"})
    assert res_unknown.status_code == 401
    assert res_unknown.json()["detail"] == "Invalid email or password."


def test_access_tokens_are_stateless_and_not_stored_in_database():
    """5.4 JWT access tokens are stateless and no token table exists in the database."""
    _, engine = get_test_app_client()
    table_names = list(Base.metadata.tables.keys())
    # Confirm no tokens or sessions table
    assert "tokens" not in table_names
    assert "access_tokens" not in table_names
    assert "refresh_tokens" not in table_names
    assert "user_tokens" not in table_names


def test_jwt_secret_loaded_from_configuration():
    """5.5 JWT secrets are loaded from environment configuration."""
    assert settings.JWT_SECRET_KEY is not None
    assert len(settings.JWT_SECRET_KEY) >= 16
    assert settings.JWT_ALGORITHM == "HS256"
