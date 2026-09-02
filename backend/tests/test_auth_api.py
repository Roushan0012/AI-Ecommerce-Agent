import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import decode_access_token, verify_password
from app.main import app
from app.models.audit_log import AuditLog
from app.models.user import User


def get_test_app_client():
    """Create test client with fresh in-memory SQLite database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client, engine


# ==============================================================================
# 1. User Registration Tests
# ==============================================================================

def test_register_user_success():
    """1. User registers successfully with valid email and password."""
    client, engine = get_test_app_client()

    payload = {
        "email": "customer.test@example.com",
        "password": "SecurePassword123!",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["email"] == "customer.test@example.com"
    assert data["is_active"] is True
    assert "created_at" in data
    assert "updated_at" in data

    # Verify no password or password_hash in response
    assert "password" not in data
    assert "password_hash" not in data
    assert "secret" not in data


def test_register_user_password_is_hashed_not_plaintext():
    """2. Password is stored as an Argon2id hash in database, never plaintext."""
    client, engine = get_test_app_client()
    raw_password = "MySuperSecretPassword2026!"

    res = client.post(
        "/api/auth/register",
        json={"email": "hashed.check@example.com", "password": raw_password},
    )
    assert res.status_code == 201
    user_id = uuid.UUID(res.json()["id"])

    with Session(engine) as session:
        user = session.query(User).filter(User.id == user_id).first()
        assert user is not None
        assert user.password_hash != raw_password
        assert "$argon2id$" in user.password_hash
        assert verify_password(raw_password, user.password_hash) is True


def test_register_user_email_normalization():
    """3. Email is trimmed and converted to lowercase during registration."""
    client, engine = get_test_app_client()

    res = client.post(
        "/api/auth/register",
        json={"email": "   User.NAME@Example.COM  ", "password": "Password123!"},
    )
    assert res.status_code == 201
    assert res.json()["email"] == "user.name@example.com"

    # Verify database contains normalized email
    with Session(engine) as session:
        user = session.query(User).filter(User.email == "user.name@example.com").first()
        assert user is not None


def test_register_user_duplicate_email_rejected():
    """4. Attempting to register an already existing email returns 409 Conflict."""
    client, engine = get_test_app_client()
    email = "duplicate@example.com"

    res1 = client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password123!"},
    )
    assert res1.status_code == 201

    # Same email in different casing/spacing
    res2 = client.post(
        "/api/auth/register",
        json={"email": "  DUPLICATE@example.com ", "password": "AnotherPassword456!"},
    )
    assert res2.status_code == 409
    assert "already registered" in res2.json()["detail"].lower()


def test_register_user_invalid_email_format_rejected():
    """5. Invalid email formats are rejected with 422 Unprocessable Entity."""
    client, engine = get_test_app_client()

    bad_emails = [
        "not-an-email",
        "missing_at_domain.com",
        "@nodomain.com",
        "user@",
        "",
    ]
    for bad_email in bad_emails:
        res = client.post(
            "/api/auth/register",
            json={"email": bad_email, "password": "ValidPassword123!"},
        )
        assert res.status_code == 422


def test_register_user_weak_or_short_password_rejected():
    """6. Passwords shorter than 8 characters or whitespace-only are rejected."""
    client, engine = get_test_app_client()

    weak_passwords = [
        "short",
        "1234567",
        "",
        "        ",
    ]
    for weak_pw in weak_passwords:
        res = client.post(
            "/api/auth/register",
            json={"email": "valid@example.com", "password": weak_pw},
        )
        assert res.status_code == 422


# ==============================================================================
# 2. User Login & Token Tests
# ==============================================================================

def test_login_user_success():
    """7. Correct login credentials return signed JWT access token."""
    client, engine = get_test_app_client()
    email = "login.success@example.com"
    password = "CorrectPassword123!"

    reg_res = client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert reg_res.status_code == 201
    user_id = reg_res.json()["id"]

    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200

    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["expires_in"] == settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

    # Verify token payload using Phase 17A decode_access_token
    payload = decode_access_token(token_data["access_token"])
    assert payload["sub"] == user_id
    assert "exp" in payload
    assert "iat" in payload


def test_login_user_email_case_insensitivity():
    """8. Login succeeds when email is submitted with mixed casing or leading/trailing whitespace."""
    client, engine = get_test_app_client()
    email = "case.test@example.com"
    password = "Password123!"

    client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )

    login_res = client.post(
        "/api/auth/login",
        json={"email": "  CASE.TEST@Example.COM  ", "password": password},
    )
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()


def test_login_user_wrong_password_rejected():
    """9. Incorrect password returns generic 401 Unauthorized error."""
    client, engine = get_test_app_client()
    email = "wrong.pass@example.com"

    client.post(
        "/api/auth/register",
        json={"email": email, "password": "RealPassword123!"},
    )

    res = client.post(
        "/api/auth/login",
        json={"email": email, "password": "WrongPassword999!"},
    )
    assert res.status_code == 401
    assert "invalid email or password" in res.json()["detail"].lower()


def test_login_user_unknown_email_rejected():
    """10. Non-existent email returns generic 401 Unauthorized without revealing user existence."""
    client, engine = get_test_app_client()

    res = client.post(
        "/api/auth/login",
        json={"email": "nonexistent.user@example.com", "password": "SomePassword123!"},
    )
    assert res.status_code == 401
    assert "invalid email or password" in res.json()["detail"].lower()


def test_login_inactive_user_rejected():
    """11. Disabled / inactive user cannot log in (returns 401)."""
    client, engine = get_test_app_client()
    email = "inactive@example.com"
    password = "Password123!"

    reg_res = client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    user_id = uuid.UUID(reg_res.json()["id"])

    # Deactivate user in database
    with Session(engine) as session:
        user = session.query(User).filter(User.id == user_id).first()
        user.is_active = False
        session.commit()

    # Attempt login
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 401
    assert "inactive" in login_res.json()["detail"].lower()


def test_auth_audit_trail_recorded():
    """12. Registration and login events record structured audit logs."""
    client, engine = get_test_app_client()
    email = "audit.auth@example.com"
    password = "Password123!"

    # 1. Register
    reg_res = client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert reg_res.status_code == 201
    user_id = uuid.UUID(reg_res.json()["id"])

    # 2. Login
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200

    # 3. Check audit logs in DB
    with Session(engine) as session:
        logs = session.query(AuditLog).filter(AuditLog.customer_id == user_id).all()
        event_types = [l.event_type for l in logs]
        assert "USER_REGISTERED" in event_types
        assert "USER_LOGIN" in event_types


def test_auth_endpoints_never_expose_secrets_or_passwords():
    """13. Auth endpoints never leak JWT secret, raw password, or password hashes."""
    client, _ = get_test_app_client()
    raw_password = "SecretPassword123!@#"

    reg_res = client.post(
        "/api/auth/register",
        json={"email": "leak.test@example.com", "password": raw_password},
    )
    reg_text = reg_res.text
    assert raw_password not in reg_text
    assert "$argon2id$" not in reg_text
    assert settings.JWT_SECRET_KEY not in reg_text

    login_res = client.post(
        "/api/auth/login",
        json={"email": "leak.test@example.com", "password": raw_password},
    )
    login_text = login_res.text
    assert raw_password not in login_text
    assert "$argon2id$" not in login_text
    assert settings.JWT_SECRET_KEY not in login_text

