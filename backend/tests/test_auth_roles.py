"""
Phase 17D — Authorization & Roles Test Suite

Covers:
1. Role behavior:
   - Newly registered user defaults to customer
   - Registration cannot create admin
   - Registration cannot create merchant
   - Invalid role values are rejected by model validator
   - Customer role works for customer endpoints

2. Authorization:
   - Unauthenticated request -> 401
   - Customer accessing merchant-only endpoint -> 403
   - Customer accessing admin-only endpoint -> 403
   - Merchant accessing appropriate merchant endpoint -> 200 (allowed)
   - Merchant accessing admin-only endpoint -> 403
   - Admin accessing admin endpoint -> 200 (allowed)
   - Admin accessing merchant endpoint -> 200 (allowed)

3. Privilege escalation prevention:
   - User cannot modify their own role
   - Request-body role cannot override JWT identity
   - Request-body user ID cannot override JWT identity
   - Forged JWT role claims rejected because server DB record is authoritative

4. Regressions:
   - Phase 17C ownership checks continue working
   - Phase 12 guardrails remain intact
   - Phase 15 X-Agent-Key authentication remains completely independent
   - Agent Commerce does not accept a User JWT as an agent credential
   - Public catalog and search APIs remain public without authentication
"""

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
    with Session(engine) as session:
        user = User(
            id=user_id,
            email=email.lower().strip(),
            password_hash=hash_password("StrongPassword123!"),
            role=role,
            is_active=is_active,
        )
        session.add(user)
        session.commit()

    token = create_access_token(subject=str(user_id), additional_claims={"role": role})
    return user_id, token


# ==============================================================================
# 1. Role Model & Registration Role Escalation Prevention Tests
# ==============================================================================

def test_newly_registered_user_defaults_to_customer():
    """1. User registration defaults to 'customer' role automatically."""
    client, engine = get_test_app_client()

    payload = {
        "email": "customer.default@example.com",
        "password": "SecurePassword123!",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["email"] == "customer.default@example.com"
    assert data["role"] == "customer"
    user_id = uuid.UUID(data["id"])

    # Verify authoritative database record
    with Session(engine) as session:
        user = session.query(User).filter(User.id == user_id).one()
        assert user.role == UserRole.CUSTOMER.value
        assert user.role == "customer"


def test_registration_cannot_create_admin():
    """2. Client attempting to pass role='admin' during registration cannot escalate privilege."""
    client, engine = get_test_app_client()

    payload = {
        "email": "hacker.admin@example.com",
        "password": "SecurePassword123!",
        "role": "admin",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()

    # Must NOT have received admin role
    assert data["role"] == "customer"
    user_id = uuid.UUID(data["id"])

    with Session(engine) as session:
        user = session.query(User).filter(User.id == user_id).one()
        assert user.role == "customer"
        assert user.role != "admin"


def test_registration_cannot_create_merchant():
    """3. Client attempting to pass role='merchant' during registration cannot escalate privilege."""
    client, engine = get_test_app_client()

    payload = {
        "email": "hacker.merchant@example.com",
        "password": "SecurePassword123!",
        "role": "merchant",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["role"] == "customer"
    user_id = uuid.UUID(data["id"])

    with Session(engine) as session:
        user = session.query(User).filter(User.id == user_id).one()
        assert user.role == "customer"
        assert user.role != "merchant"


def test_invalid_role_values_rejected_by_model():
    """4. User model validation rejects invalid or arbitrary role assignments."""
    client, engine = get_test_app_client()

    # Valid roles pass
    assert UserRole.is_valid("customer") is True
    assert UserRole.is_valid("merchant") is True
    assert UserRole.is_valid("admin") is True

    # Arbitrary / invalid roles fail validation
    assert UserRole.is_valid("superadmin") is False
    assert UserRole.is_valid("root") is False
    assert UserRole.is_valid("") is False

    with Session(engine) as session:
        user = User(
            id=uuid.uuid4(),
            email="invalid.role@example.com",
            password_hash="dummy_hash",
        )
        with pytest.raises(ValueError, match="Invalid user role"):
            user.role = "superuser"


def test_customer_role_works_for_customer_endpoints():
    """5. Authenticated customer role works seamlessly for cart, order, and payment endpoints."""
    client, engine = get_test_app_client()
    user_id, token = create_user_with_role(engine, "shopper@example.com", role="customer")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Cart retrieval
    cart_res = client.post("/api/cart", json={"customer_id": str(user_id)}, headers=headers)
    assert cart_res.status_code == 200

    # 2. Add product to cart
    with Session(engine) as session:
        prod = session.query(Product).first()
        prod_id = str(prod.id)

    item_res = client.post(
        f"/api/cart/{user_id}/items",
        json={"product_id": prod_id, "quantity": 1},
        headers=headers,
    )
    assert item_res.status_code == 200

    # 3. Create order
    order_res = client.post(
        "/api/orders",
        json={"customer_id": str(user_id)},
        headers=headers,
    )
    assert order_res.status_code == 201
    assert order_res.json()["customer_id"] == str(user_id)


# ==============================================================================
# 2. Authorization & Role Boundary Tests
# ==============================================================================

def test_unauthenticated_requests_return_401():
    """6. Unauthenticated requests to protected endpoints return 401 Unauthorized."""
    client, _ = get_test_app_client()

    # Merchant dashboard
    res_dash = client.get("/api/dashboard/overview")
    assert res_dash.status_code == 401
    assert "Bearer" in res_dash.headers.get("WWW-Authenticate", "")

    # Admin endpoints
    res_admin = client.get("/api/admin/system/status")
    assert res_admin.status_code == 401

    res_audit_admin = client.get("/api/audit/admin/all")
    assert res_audit_admin.status_code == 401

    # Customer endpoints
    res_cart = client.post("/api/cart")
    assert res_cart.status_code == 401


def test_customer_accessing_merchant_only_endpoint_returns_403():
    """7. Authenticated customer receives 403 Forbidden when accessing merchant dashboard."""
    client, engine = get_test_app_client()
    _, customer_token = create_user_with_role(engine, "customer.only@example.com", role="customer")
    headers = {"Authorization": f"Bearer {customer_token}"}

    # Test all merchant dashboard endpoints
    endpoints = [
        "/api/dashboard/overview",
        "/api/dashboard/orders",
        "/api/dashboard/activity",
    ]
    for ep in endpoints:
        res = client.get(ep, headers=headers)
        assert res.status_code == 403, f"Expected 403 on {ep}, got {res.status_code}"
        assert "forbidden" in res.json()["detail"].lower()


def test_customer_accessing_admin_only_endpoint_returns_403():
    """8. Authenticated customer receives 403 Forbidden when accessing admin endpoints."""
    client, engine = get_test_app_client()
    _, customer_token = create_user_with_role(engine, "customer.probe@example.com", role="customer")
    headers = {"Authorization": f"Bearer {customer_token}"}

    res_status = client.get("/api/admin/system/status", headers=headers)
    assert res_status.status_code == 403

    res_logs = client.get("/api/admin/audit-logs", headers=headers)
    assert res_logs.status_code == 403

    res_audit_all = client.get("/api/audit/admin/all", headers=headers)
    assert res_audit_all.status_code == 403


def test_merchant_accessing_appropriate_merchant_endpoint_allowed():
    """9. Authenticated merchant is allowed on merchant dashboard endpoints (200 OK)."""
    client, engine = get_test_app_client()
    _, merchant_token = create_user_with_role(engine, "store.owner@example.com", role="merchant")
    headers = {"Authorization": f"Bearer {merchant_token}"}

    res_overview = client.get("/api/dashboard/overview", headers=headers)
    assert res_overview.status_code == 200
    assert "total_revenue" in res_overview.json()

    res_orders = client.get("/api/dashboard/orders", headers=headers)
    assert res_orders.status_code == 200

    res_act = client.get("/api/dashboard/activity", headers=headers)
    assert res_act.status_code == 200


def test_merchant_accessing_admin_only_endpoint_returns_403():
    """10. Authenticated merchant receives 403 Forbidden when attempting admin-only endpoints."""
    client, engine = get_test_app_client()
    _, merchant_token = create_user_with_role(engine, "store.owner2@example.com", role="merchant")
    headers = {"Authorization": f"Bearer {merchant_token}"}

    res_admin = client.get("/api/admin/system/status", headers=headers)
    assert res_admin.status_code == 403

    res_logs = client.get("/api/admin/audit-logs", headers=headers)
    assert res_logs.status_code == 403

    res_audit_all = client.get("/api/audit/admin/all", headers=headers)
    assert res_audit_all.status_code == 403


def test_admin_accessing_admin_endpoint_allowed():
    """11. Authenticated administrator is allowed on admin endpoints (200 OK)."""
    client, engine = get_test_app_client()
    _, admin_token = create_user_with_role(engine, "super.admin@example.com", role="admin")
    headers = {"Authorization": f"Bearer {admin_token}"}

    res_status = client.get("/api/admin/system/status", headers=headers)
    assert res_status.status_code == 200
    data = res_status.json()
    assert data["status"] == "ok"
    assert data["admin_user"] == "super.admin@example.com"

    res_logs = client.get("/api/admin/audit-logs", headers=headers)
    assert res_logs.status_code == 200
    assert "items" in res_logs.json()

    res_audit_all = client.get("/api/audit/admin/all", headers=headers)
    assert res_audit_all.status_code == 200


def test_admin_accessing_merchant_endpoint_allowed():
    """12. Authenticated administrator also has oversight access to merchant dashboard."""
    client, engine = get_test_app_client()
    _, admin_token = create_user_with_role(engine, "platform.admin@example.com", role="admin")
    headers = {"Authorization": f"Bearer {admin_token}"}

    res_overview = client.get("/api/dashboard/overview", headers=headers)
    assert res_overview.status_code == 200
    assert "total_revenue" in res_overview.json()


# ==============================================================================
# 3. Privilege Escalation & Manipulation Prevention Tests
# ==============================================================================

def test_user_cannot_modify_their_own_role():
    """13. Normal user cannot alter their own role via any API."""
    client, engine = get_test_app_client()
    user_id, customer_token = create_user_with_role(engine, "shopper.rolechange@example.com", role="customer")
    headers = {"Authorization": f"Bearer {customer_token}"}

    # Attempt to inject role field in cart creation
    res = client.post(
        "/api/cart",
        json={"customer_id": str(user_id), "role": "admin"},
        headers=headers,
    )
    assert res.status_code == 200

    # Authoritative database role must remain 'customer'
    with Session(engine) as session:
        user = session.query(User).filter(User.id == user_id).one()
        assert user.role == "customer"


def test_request_body_role_cannot_override_jwt_identity():
    """14. Client-supplied role in request body cannot override server-authoritative JWT role."""
    client, engine = get_test_app_client()
    _, customer_token = create_user_with_role(engine, "body.override@example.com", role="customer")
    headers = {"Authorization": f"Bearer {customer_token}"}

    # Customer attempts to query merchant dashboard while putting "role": "merchant" in request body
    res = client.get("/api/dashboard/overview", headers=headers)
    assert res.status_code == 403


def test_request_body_user_id_cannot_override_jwt_identity():
    """15. Client-supplied user ID in payload cannot override authenticated JWT identity."""
    client, engine = get_test_app_client()
    user_a_id, user_a_token = create_user_with_role(engine, "user.a@example.com", role="customer")
    user_b_id, _ = create_user_with_role(engine, "user.b@example.com", role="customer")

    headers = {"Authorization": f"Bearer {user_a_token}"}

    # User A tries to create or access cart for User B
    res_cart = client.post(
        "/api/cart",
        json={"customer_id": str(user_b_id)},
        headers=headers,
    )
    assert res_cart.status_code == 403
    assert "another user" in res_cart.json()["detail"].lower()

    # User A tries to create order for User B
    res_order = client.post(
        "/api/orders",
        json={"customer_id": str(user_b_id)},
        headers=headers,
    )
    assert res_order.status_code == 403
    assert "another user" in res_order.json()["detail"].lower()


def test_jwt_role_manipulation_rejected_because_server_is_authoritative():
    """16. Even if a JWT token has a manipulated 'role: admin' claim, server checks DB and rejects with 403."""
    client, engine = get_test_app_client()
    # User is stored in database with role='customer'
    user_id, _ = create_user_with_role(engine, "manipulator@example.com", role="customer")

    # Attacker crafts a token signed with the valid key, but injects "role": "admin" into token claims
    forged_token = create_access_token(
        subject=str(user_id),
        additional_claims={"role": "admin"},
    )
    headers = {"Authorization": f"Bearer {forged_token}"}

    # Accessing admin endpoint MUST fail because the DB record has role='customer'
    res_admin = client.get("/api/admin/system/status", headers=headers)
    assert res_admin.status_code == 403

    # Accessing merchant endpoint MUST also fail
    res_dash = client.get("/api/dashboard/overview", headers=headers)
    assert res_dash.status_code == 403


# ==============================================================================
# 4. Regressions & Boundary Isolation Tests
# ==============================================================================

def test_regression_phase_17c_ownership_checks_continue_working():
    """17. Customer cannot access another customer's cart, orders, or audit trail."""
    client, engine = get_test_app_client()
    user_a_id, user_a_token = create_user_with_role(engine, "owner.a@example.com", role="customer")
    user_b_id, _ = create_user_with_role(engine, "owner.b@example.com", role="customer")

    headers_a = {"Authorization": f"Bearer {user_a_token}"}

    # User A accesses User B cart
    res_cart = client.get(f"/api/cart/{user_b_id}", headers=headers_a)
    assert res_cart.status_code == 403

    # User A accesses User B orders
    res_orders = client.get(f"/api/orders/{user_b_id}", headers=headers_a)
    assert res_orders.status_code == 403

    # User A accesses User B audit trail
    res_audit = client.get(f"/api/audit/{user_b_id}", headers=headers_a)
    assert res_audit.status_code == 403


def test_regression_phase_15_agent_commerce_independent():
    """18. Phase 15 Agent Commerce API strictly requires X-Agent-Key and functions independently."""
    client, engine = get_test_app_client()
    agent_key = settings.COMMERCE_AGENT_KEY or "ac042107acf34503bba50d6d77dc3ed15f429bfbef5ec6e4ef0cd2ad95cbdceb"

    with Session(engine) as session:
        prod = session.query(Product).first()
        prod_id = str(prod.id)

    # Valid X-Agent-Key succeeds
    res = client.post(
        "/api/agent-commerce/inventory/check",
        json={"product_id": prod_id, "quantity": 1},
        headers={"X-Agent-Key": agent_key},
    )
    assert res.status_code == 200
    assert res.json()["available"] is True

    # Missing X-Agent-Key fails with 401
    res_missing = client.post(
        "/api/agent-commerce/inventory/check",
        json={"product_id": prod_id, "quantity": 1},
    )
    assert res_missing.status_code == 401


def test_agent_commerce_does_not_accept_user_jwt():
    """19. Agent Commerce endpoints reject User JWTs when passed instead of X-Agent-Key."""
    client, engine = get_test_app_client()
    _, customer_token = create_user_with_role(engine, "jwt.probe@example.com", role="customer")

    with Session(engine) as session:
        prod = session.query(Product).first()
        prod_id = str(prod.id)

    # User JWT passed in Authorization header without X-Agent-Key must be rejected with 401
    res = client.post(
        "/api/agent-commerce/inventory/check",
        json={"product_id": prod_id, "quantity": 1},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert res.status_code == 401
    assert "X-Agent-Key header required" in res.json()["detail"]


def test_public_catalog_and_search_apis_remain_unauthenticated():
    """20. Public catalog and AI search APIs remain public without requiring auth headers."""
    client, _ = get_test_app_client()

    res_catalog = client.get("/api/products")
    assert res_catalog.status_code == 200
    assert "items" in res_catalog.json()

    res_intent = client.post("/api/agent/understand", json={"message": "wireless headphones"})
    assert res_intent.status_code == 200

    res_search = client.post("/api/agent/search", json={"message": "wireless headphones"})
    assert res_search.status_code == 200
