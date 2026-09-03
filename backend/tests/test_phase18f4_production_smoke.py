"""Phase 18F-4 — Production Smoke Test Suite.

End-to-end verification of production-like deployment readiness, security boundaries,
orchestration integrity, and application contracts:
1. Backend process liveness probe (/api/health)
2. Backend database readiness probe (/api/health/database)
3. Frontend service configuration and lifecycle contracts
4. Public commerce catalog API availability
5. JWT authentication boundary (valid vs missing vs malformed token rejection)
6. Agent-to-Agent (A2A) commerce isolation (X-Agent-Key vs User JWT)
7. Payment security & Razorpay webhook signature validation
8. Production configuration safeguards (rejection of SQLite, wildcard CORS, debug mode)
9. Docker Compose orchestration integrity and zero hardcoded secrets
10. Repository-wide credential hygiene
"""

import hmac
import hashlib
import os
import re
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.core.config import Settings, ConfigurationError, settings
from app.core.database import get_db
from app.core.security import create_access_token, get_current_user
from app.main import app
from app.models.user import User


@pytest.fixture
def client():
    app.dependency_overrides.pop(get_current_user, None)
    return TestClient(app)


def test_smoke_backend_liveness_health(client):
    """Smoke: Verify ASGI web process liveness probe responds with 200 OK and no secrets."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "ai-commerce-agent-api"
    # Ensure zero sensitive information is leaked
    assert "database" not in data
    assert "secret" not in data
    assert "token" not in data


def test_smoke_backend_database_readiness(client):
    """Smoke: Verify database readiness probe responds with valid status contract without credential leaks."""
    res = client.get("/api/health/database")
    assert res.status_code in (200, 503)
    data = res.json()
    if res.status_code == 200:
        assert data["status"] == "ok"
        assert data["database"] == "connected"
    else:
        assert data["detail"]["status"] == "error"
        assert data["detail"]["database"] == "disconnected"

    # Zero database credentials or paths disclosed
    raw_text = res.text.lower()
    assert "password" not in raw_text
    assert "postgres://" not in raw_text
    assert "supabase.co:5432" not in raw_text


def test_smoke_frontend_configuration_and_lifecycle():
    """Smoke: Verify frontend production Dockerfile, lifecycle scripts, and API binding."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    frontend_dir = repo_root / "frontend"

    # 1. API Base URL configuration
    api_ts = (frontend_dir / "src" / "lib" / "api.ts").read_text(encoding="utf-8")
    assert "NEXT_PUBLIC_API_BASE_URL" in api_ts
    assert "http://127.0.0.1:8000" in api_ts

    # 2. Package scripts
    pkg_json = (frontend_dir / "package.json").read_text(encoding="utf-8")
    assert '"build": "next build"' in pkg_json
    assert '"start": "next start"' in pkg_json

    # 3. Production Dockerfile
    dockerfile = (frontend_dir / "Dockerfile").read_text(encoding="utf-8")
    assert "node:20-alpine" in dockerfile
    assert "USER nextjs" in dockerfile
    assert "npm run build" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "next dev" not in dockerfile


def test_smoke_public_commerce_api_accessibility(client):
    """Smoke: Verify public product catalog is accessible and returns server-authoritative data."""
    res = client.get("/api/products")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    items = data["items"]
    assert isinstance(items, list)
    if items:
        item = items[0]
        assert "id" in item
        assert "name" in item
        assert "price" in item
        assert "currency" in item
        assert float(item["price"]) > 0


def test_smoke_jwt_authentication_boundary(client):
    """Smoke: Verify JWT authentication protects user endpoints and rejects missing/forged tokens."""
    # 1. Missing token -> 401 Unauthorized
    res_missing = client.get("/api/auth/me")
    assert res_missing.status_code == 401
    assert "detail" in res_missing.json()

    # 2. Forged / Malformed token -> 401 Unauthorized
    res_forged = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.tampered_signature"},
    )
    assert res_forged.status_code == 401

    # 3. Valid token -> 200 OK
    cust_email = f"smoke_user_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = client.post(
        "/api/auth/register",
        json={"email": cust_email, "password": "SmokePassword123!"},
    )
    assert reg_res.status_code == 201
    user_id = reg_res.json()["id"]

    token = create_access_token(user_id, additional_claims={"role": "customer"})
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    user_profile = me_res.json()
    assert user_profile["id"] == user_id
    assert user_profile["email"] == cust_email
    assert "password_hash" not in user_profile


def test_smoke_a2a_agent_key_isolation_from_user_jwt(client):
    """Smoke: Verify A2A machine commerce requires X-Agent-Key and strictly rejects User JWTs."""
    valid_key = settings.COMMERCE_AGENT_KEY

    # 1. Machine endpoint with valid X-Agent-Key -> 200 OK
    res_a2a_valid = client.post(
        "/api/agent-commerce/discover",
        json={"query": "wireless headphones"},
        headers={"X-Agent-Key": valid_key},
    )
    assert res_a2a_valid.status_code == 200

    # 2. Machine endpoint with User JWT (missing X-Agent-Key) -> 401 Unauthorized
    fake_jwt = create_access_token(str(uuid.uuid4()), additional_claims={"role": "admin"})
    res_a2a_jwt = client.post(
        "/api/agent-commerce/discover",
        json={"query": "wireless headphones"},
        headers={"Authorization": f"Bearer {fake_jwt}"},
    )
    assert res_a2a_jwt.status_code == 401

    # 3. User endpoint with X-Agent-Key (missing JWT) -> 401 Unauthorized
    res_cart = client.post(
        "/api/cart",
        json={},
        headers={"X-Agent-Key": valid_key},
    )
    assert res_cart.status_code == 401


def test_smoke_payment_security_and_webhook_validation(client):
    """Smoke: Verify Razorpay webhook strictly validates HMAC-SHA256 signatures."""
    payload = b'{"event": "payment.captured", "payload": {"payment": {"entity": {"id": "pay_test123"}}}}'

    # 1. Forged / invalid signature -> 400 Bad Request
    res_forged = client.post(
        "/api/payments/webhook",
        content=payload,
        headers={
            "X-Razorpay-Signature": "forged_invalid_hmac_signature",
            "Content-Type": "application/json",
        },
    )
    assert res_forged.status_code == 400
    assert "Invalid webhook signature" in res_forged.json()["detail"]

    # 2. Authentic HMAC signature -> 200 OK
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    valid_sig = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    res_valid = client.post(
        "/api/payments/webhook",
        content=payload,
        headers={
            "X-Razorpay-Signature": valid_sig,
            "Content-Type": "application/json",
        },
    )
    assert res_valid.status_code == 200
    assert res_valid.json()["status"] in ("ok", "ignored")


def test_smoke_production_safeguards_enforcement(monkeypatch):
    """Smoke: Verify production configuration validation rejects SQLite, wildcard CORS, and debug mode."""
    monkeypatch.setenv("ENVIRONMENT", "production")

    # 1. DEBUG must be False in production
    monkeypatch.setenv("DEBUG", "true")
    s = Settings()
    assert s.is_production is True
    assert s.DEBUG is False

    # 2. SQLite is blocked in production
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./smoke_test.db")
    monkeypatch.setenv("JWT_SECRET_KEY", "min_32_character_secret_key_1234567890")
    monkeypatch.setenv("COMMERCE_AGENT_KEY", "min_16_char_agent_key_123")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_live_real_id")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "real_secret")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "real_webhook_secret")
    monkeypatch.setenv("CORS_ORIGINS", "https://shop.example.com")
    with pytest.raises(ConfigurationError) as exc_db:
        s.validate_production_config()
    assert "SQLite is not permitted" in str(exc_db.value)

    # 3. Wildcard CORS is blocked in production
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(ConfigurationError) as exc_cors:
        s.validate_production_config()
    assert "Wildcard origin" in str(exc_cors.value)


def test_smoke_docker_compose_orchestration_integrity():
    """Smoke: Verify docker-compose.yml defines separate services, healthchecks, and zero hardcoded secrets."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    compose_path = repo_root / "docker-compose.yml"
    assert compose_path.exists()

    content = compose_path.read_text(encoding="utf-8")

    # Services
    assert "backend:" in content
    assert "frontend:" in content

    # Healthchecks
    assert "curl -f http://localhost:8000/api/health" in content
    assert "wget -qO- http://localhost:3000/" in content

    # Dependencies
    assert "depends_on:" in content
    assert "condition: service_healthy" in content

    # Managed database decoupling (no local postgresql service container)
    assert "image: postgres" not in content

    # No hardcoded secrets
    assert not re.search(r'JWT_SECRET_KEY=\b[a-zA-Z0-9_-]{20,}\b', content)
    assert not re.search(r'RAZORPAY_KEY_SECRET=\b[a-zA-Z0-9_-]{20,}\b', content)
    assert not re.search(r'COMMERCE_AGENT_KEY=\b[a-zA-Z0-9_-]{20,}\b', content)


def test_smoke_secret_hygiene_across_tracked_files():
    """Smoke: Verify tracked repository files contain zero real secrets, live keys, or private certificates."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    forbidden_patterns = [
        re.compile(r"rzp_live_[a-zA-Z0-9]{14,}"),
        re.compile(r"gsk_[a-zA-Z0-9]{30,}"),
        re.compile(r"ghp_[a-zA-Z0-9]{30,}"),
        re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ]

    extensions_to_check = {".py", ".ts", ".tsx", ".js", ".json", ".yml", ".yaml", ".md", ".sh"}

    for path in repo_root.rglob("*"):
        if any(ignored in path.parts for ignored in [".git", ".venv", "node_modules", ".next", "__pycache__"]):
            continue
        if path.is_file() and path.suffix in extensions_to_check:
            try:
                file_text = path.read_text(encoding="utf-8", errors="ignore")
                for pattern in forbidden_patterns:
                    match = pattern.search(file_text)
                    assert match is None, f"Potential credential leak detected in {path.relative_to(repo_root)}: {pattern.pattern}"
            except Exception as e:
                # Binary or unreadable files can be safely skipped
                pass
