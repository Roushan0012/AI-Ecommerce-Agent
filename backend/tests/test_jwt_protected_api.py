import uuid
from datetime import timedelta
import jwt
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
from app.models.user import User


def get_test_app_client():
    """Create test client with clean in-memory SQLite DB with seeded products and clean overrides."""
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


def create_user_and_token(engine, email: str, is_active: bool = True):
    """Helper to create a test user and generate their signed JWT access token."""
    user_id = uuid.uuid4()
    with Session(engine) as session:
        user = User(
            id=user_id,
            email=email.lower().strip(),
            password_hash=hash_password("StrongPassword123!"),
            is_active=is_active,
        )
        session.add(user)
        session.commit()

    token = create_access_token(subject=str(user_id))
    return user_id, token


# ==============================================================================
# 1. Authentication Tests (Protected Endpoints)
# ==============================================================================

def test_protected_cart_endpoint_without_jwt_returns_401():
    """1. Accessing protected cart endpoint without Authorization header returns 401."""
    client, _ = get_test_app_client()
    res = client.post("/api/cart", json={})
    assert res.status_code == 401
    assert "missing authorization header" in res.json()["detail"].lower()


def test_protected_orders_endpoint_without_jwt_returns_401():
    """2. Accessing protected orders endpoint without Authorization header returns 401."""
    client, _ = get_test_app_client()
    res = client.post("/api/orders", json={"cart_id": str(uuid.uuid4())})
    assert res.status_code == 401


def test_protected_endpoint_malformed_authorization_header_returns_401():
    """3. Malformed Authorization headers (no space, empty token) return 401."""
    client, _ = get_test_app_client()

    bad_headers = [
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer    "},
        {"Authorization": "BearerTokenWithoutSpace"},
        {"Authorization": ""},
    ]

    for headers in bad_headers:
        res = client.post("/api/cart", json={}, headers=headers)
        assert res.status_code == 401
        assert "authorization" in res.json()["detail"].lower() or "token" in res.json()["detail"].lower()


def test_protected_endpoint_non_bearer_scheme_returns_401():
    """4. Non-Bearer schemes (Basic, Token, Digest) return 401."""
    client, _ = get_test_app_client()

    res = client.post(
        "/api/cart",
        json={},
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert res.status_code == 401
    assert "bearer token required" in res.json()["detail"].lower()


def test_protected_endpoint_invalid_jwt_signature_returns_401():
    """5. JWT signed with wrong secret key returns 401."""
    client, engine = get_test_app_client()
    user_id, _ = create_user_and_token(engine, "forged@example.com")

    # Sign with forged secret
    forged_token = jwt.encode(
        {"sub": str(user_id), "iat": 100000, "exp": 9999999999},
        "wrong_cryptographic_secret_key_12345",
        algorithm="HS256",
    )

    res = client.post(
        "/api/cart",
        json={},
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    assert res.status_code == 401
    assert "invalid access token" in res.json()["detail"].lower()


def test_protected_endpoint_expired_jwt_returns_401():
    """6. Expired JWT access token returns 401."""
    client, engine = get_test_app_client()
    user_id, _ = create_user_and_token(engine, "expired@example.com")

    expired_token = create_access_token(
        subject=str(user_id),
        expires_delta=timedelta(seconds=-30),  # expired 30s ago
    )

    res = client.post(
        "/api/cart",
        json={},
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()


def test_protected_endpoint_malformed_jwt_string_returns_401():
    """7. Completely malformed JWT string returns 401."""
    client, _ = get_test_app_client()

    res = client.post(
        "/api/cart",
        json={},
        headers={"Authorization": "Bearer not.a.valid.jwt.payload"},
    )
    assert res.status_code == 401
    assert "invalid access token" in res.json()["detail"].lower()


def test_protected_endpoint_nonexistent_user_sub_returns_401():
    """8. Valid JWT with subject UUID not in DB returns 401."""
    client, _ = get_test_app_client()
    nonexistent_user_id = uuid.uuid4()
    token = create_access_token(subject=str(nonexistent_user_id))

    res = client.post(
        "/api/cart",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 401
    assert "user not found" in res.json()["detail"].lower()


def test_protected_endpoint_inactive_user_returns_401():
    """9. JWT for inactive / deactivated user account returns 401."""
    client, engine = get_test_app_client()
    _, token = create_user_and_token(engine, "inactive.jwt@example.com", is_active=False)

    res = client.post(
        "/api/cart",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 401
    assert "inactive" in res.json()["detail"].lower()


def test_protected_endpoint_valid_jwt_allows_access():
    """10. Valid active user JWT allows access to cart endpoint."""
    client, engine = get_test_app_client()
    user_id, token = create_user_and_token(engine, "valid.jwt@example.com")

    res = client.post(
        "/api/cart",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["customer_id"] == str(user_id)
    assert data["status"] == "active"


# ==============================================================================
# 2. Authorization & Ownership Tests (Cross-User Isolation)
# ==============================================================================

def test_user_a_can_access_own_cart_and_items():
    """11. User A can add items to and query their own cart with valid JWT."""
    client, engine = get_test_app_client()
    user_a, token_a = create_user_and_token(engine, "usera@example.com")

    with Session(engine) as session:
        prod = session.query(Product).first()
        prod_id = str(prod.id)

    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Add item
    add_res = client.post(
        f"/api/cart/{user_a}/items",
        json={"product_id": prod_id, "quantity": 2},
        headers=headers_a,
    )
    assert add_res.status_code == 200
    assert len(add_res.json()["items"]) == 1

    # Get cart
    get_res = client.get(f"/api/cart/{user_a}", headers=headers_a)
    assert get_res.status_code == 200
    assert get_res.json()["customer_id"] == str(user_a)


def test_user_a_cannot_access_user_b_cart():
    """12. User A cannot view, add items to, or modify User B's cart (403 Forbidden)."""
    client, engine = get_test_app_client()
    user_a, token_a = create_user_and_token(engine, "usera.isolation@example.com")
    user_b, token_b = create_user_and_token(engine, "userb.isolation@example.com")

    with Session(engine) as session:
        prod = session.query(Product).first()
        prod_id = str(prod.id)

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B primes their cart
    client.post(
        f"/api/cart/{user_b}/items",
        json={"product_id": prod_id, "quantity": 1},
        headers=headers_b,
    )

    # User A attempts to read User B's cart
    res_get = client.get(f"/api/cart/{user_b}", headers=headers_a)
    assert res_get.status_code == 403
    assert "access denied" in res_get.json()["detail"].lower()

    # User A attempts to add item to User B's cart
    res_add = client.post(
        f"/api/cart/{user_b}/items",
        json={"product_id": prod_id, "quantity": 1},
        headers=headers_a,
    )
    assert res_add.status_code == 403

    # User A attempts to delete item from User B's cart
    res_del = client.delete(
        f"/api/cart/{user_b}/items/{prod_id}",
        headers=headers_a,
    )
    assert res_del.status_code == 403


def test_user_a_cannot_access_user_b_orders_or_payments():
    """13. User A cannot checkout or initiate payment on User B's behalf."""
    client, engine = get_test_app_client()
    user_a, token_a = create_user_and_token(engine, "usera.orders@example.com")
    user_b, token_b = create_user_and_token(engine, "userb.orders@example.com")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    with Session(engine) as session:
        prod = session.query(Product).first()
        prod_id = str(prod.id)

    # User B creates a cart and order
    client.post(
        f"/api/cart/{user_b}/items",
        json={"product_id": prod_id, "quantity": 1},
        headers=headers_b,
    )
    order_b_res = client.post(
        "/api/orders",
        json={"customer_id": str(user_b)},
        headers=headers_b,
    )
    assert order_b_res.status_code == 201
    order_b_id = order_b_res.json()["id"]

    # User A attempts to list User B's orders
    list_res = client.get(f"/api/orders/{user_b}", headers=headers_a)
    assert list_res.status_code == 403

    # User A attempts to get User B's order detail
    detail_res = client.get(f"/api/orders/{user_b}/{order_b_id}", headers=headers_a)
    assert detail_res.status_code == 403

    # User A attempts to initiate payment on User B's order
    pay_res = client.post(
        "/api/payments/create-order",
        json={"order_id": order_b_id, "customer_id": str(user_b)},
        headers=headers_a,
    )
    assert pay_res.status_code == 403

    # User A attempts to read User B's audit trail
    audit_res = client.get(f"/api/audit/{user_b}", headers=headers_a)
    assert audit_res.status_code == 403


def test_client_supplied_user_id_cannot_override_jwt_identity():
    """14. Passing a different customer_id in body while authenticated as User A is rejected."""
    client, engine = get_test_app_client()
    user_a, token_a = create_user_and_token(engine, "usera.override@example.com")
    fake_user_id = str(uuid.uuid4())

    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Attempt to create cart for fake_user_id while logged in as User A
    cart_res = client.post(
        "/api/cart",
        json={"customer_id": fake_user_id},
        headers=headers_a,
    )
    assert cart_res.status_code == 403
    assert "cannot access or create cart for another user" in cart_res.json()["detail"].lower()


# ==============================================================================
# 3. Public vs Protected Boundary & Regression Tests
# ==============================================================================

def test_public_registration_and_login_remain_accessible_without_jwt():
    """15. Public auth endpoints (/api/auth/register, /api/auth/login) require no JWT."""
    client, _ = get_test_app_client()

    reg_res = client.post(
        "/api/auth/register",
        json={"email": "public.test@example.com", "password": "Password123!"},
    )
    assert reg_res.status_code == 201

    login_res = client.post(
        "/api/auth/login",
        json={"email": "public.test@example.com", "password": "Password123!"},
    )
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()


def test_public_catalog_and_agent_discovery_remain_accessible_without_jwt():
    """16. Public catalog (/api/products) and AI search endpoints require no JWT."""
    client, _ = get_test_app_client()

    # Catalog listing
    prod_res = client.get("/api/products")
    assert prod_res.status_code == 200

    # AI search
    search_res = client.post("/api/agent/search", json={"message": "wireless earbuds under 5000"})
    assert search_res.status_code == 200


def test_phase_15_agent_commerce_requires_agent_key_not_jwt():
    """17. Agent commerce (/api/agent-commerce/*) requires X-Agent-Key, rejects JWT."""
    client, engine = get_test_app_client()
    _, token = create_user_and_token(engine, "agent.jwt@example.com")

    # Attempt with JWT in Authorization header -> rejected (requires X-Agent-Key)
    res_with_jwt = client.post(
        "/api/agent-commerce/discover",
        json={"query": "earbuds"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_with_jwt.status_code == 401

    # Valid X-Agent-Key succeeds
    res_with_key = client.post(
        "/api/agent-commerce/discover",
        json={"query": "earbuds"},
        headers={"X-Agent-Key": settings.COMMERCE_AGENT_KEY or "agy_live_test_commerce_secret_2026_key"},
    )
    assert res_with_key.status_code == 200
