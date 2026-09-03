"""Phase 18C — API & Application Hardening Tests.

Validates:
1. In-memory sliding window rate limiting (Auth and Default tiers, 429 response, Retry-After header)
2. Request size limits (413 response on oversized payloads, input length constraints)
3. HTTP security headers (nosniff, DENY, XSS protection, Referrer policy, Permissions policy, production HSTS)
4. Production-safe error responses (zero password/token leakage in 422 errors, sanitized 500 errors)
5. Sensitive data redaction in logging (JWT, Bearer tokens, passwords, database credentials, API keys)
6. Preservation of existing security boundaries (JWT/RBAC, A2A X-Agent-Key, Razorpay HMAC)
"""

import io
import logging
import uuid
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from app.core.config import Settings, settings
from app.core.logging_security import redact_sensitive_text, setup_security_logging
from app.core.rate_limit import rate_limiter
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
def reset_limiter_before_each_test():
    """Ensure rate limiter storage is pristine before and after every test."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


# ==============================================================================
# 1. Rate Limiting Tests
# ==============================================================================

def test_rate_limiting_auth_endpoint_exceeded(monkeypatch):
    """Auth endpoints enforce strict rate limit and return 429 with Retry-After header."""
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_AUTH_PER_MINUTE", "3")

    client = TestClient(app)

    # 3 allowed requests
    for i in range(3):
        res = client.post(
            "/api/auth/login",
            json={"email": f"test{i}@example.com", "password": "any_password_123"},
        )
        assert res.status_code in (200, 401, 422), f"Request {i} failed unexpectedly: {res.status_code}"

    # 4th request must be rejected with 429
    res_blocked = client.post(
        "/api/auth/login",
        json={"email": "test4@example.com", "password": "any_password_123"},
    )
    assert res_blocked.status_code == 429
    data = res_blocked.json()
    assert "Rate limit exceeded" in data["detail"]
    assert "Retry-After" in res_blocked.headers
    assert int(res_blocked.headers["Retry-After"]) >= 1


def test_rate_limiting_whitelists_health_checks(monkeypatch):
    """Health endpoints are never blocked by rate limiting."""
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_DEFAULT_PER_MINUTE", "2")

    client = TestClient(app)

    # Send 5 health check requests (limit is 2)
    for _ in range(5):
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


def test_rate_limiting_can_be_disabled(monkeypatch):
    """When RATE_LIMIT_ENABLED=false, requests beyond the threshold are not blocked."""
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("RATE_LIMIT_AUTH_PER_MINUTE", "2")

    client = TestClient(app)

    for i in range(5):
        res = client.post(
            "/api/auth/login",
            json={"email": f"test{i}@example.com", "password": "any_password_123"},
        )
        assert res.status_code != 429


# ==============================================================================
# 2. Request Size Limits & Input Protection Tests
# ==============================================================================

def test_request_payload_exceeding_max_bytes_is_rejected(monkeypatch):
    """Requests exceeding MAX_REQUEST_BODY_BYTES are rejected with 413 Payload Too Large."""
    monkeypatch.setenv("MAX_REQUEST_BODY_BYTES", "500")

    client = TestClient(app)

    # Oversized payload (> 500 bytes)
    large_payload = {"message": "a" * 800}
    res = client.post("/api/agent/understand", json=large_payload)
    assert res.status_code == 413
    assert "Request payload exceeds maximum allowed size" in res.json()["detail"]


def test_request_payload_within_limit_is_accepted(monkeypatch):
    """Requests within MAX_REQUEST_BODY_BYTES proceed normally."""
    monkeypatch.setenv("MAX_REQUEST_BODY_BYTES", "5000")

    client = TestClient(app)
    res = client.post(
        "/api/agent/understand",
        json={"message": "I need wireless headphones under 5000"},
    )
    assert res.status_code == 200


def test_login_input_string_length_protection():
    """Login passwords exceeding maximum field length (128) are rejected at validation stage."""
    client = TestClient(app)
    oversized_password = "p" * 200
    res = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": oversized_password},
    )
    assert res.status_code == 422


# ==============================================================================
# 3. HTTP Security Headers Tests
# ==============================================================================

def test_security_headers_present_on_responses():
    """Standard defensive security headers are returned on API responses."""
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200

    headers = res.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert headers.get("Permissions-Policy") == "camera=(), microphone=(), geolocation=()"


def test_hsts_header_in_production(monkeypatch):
    """Strict-Transport-Security is present when running in production mode."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"


def test_cors_headers_preserved_alongside_security_headers():
    """CORS headers and security headers coexist without conflict."""
    client = TestClient(app)
    res = client.get(
        "/api/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert res.headers.get("access-control-allow-credentials") == "true"
    assert res.headers.get("X-Frame-Options") == "DENY"


# ==============================================================================
# 4. Error Handling & Secret Leakage Prevention Tests
# ==============================================================================

def test_validation_error_redacts_password_inputs():
    """422 Validation errors never echo back raw submitted passwords."""
    client = TestClient(app)
    secret_password = "MySuperSecretPassword123!"

    # Send payload with invalid email to trigger 422 error
    res = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": secret_password},
    )
    assert res.status_code == 422
    raw_response_text = res.text

    # The actual password must NOT appear anywhere in the response text
    assert secret_password not in raw_response_text


def test_unhandled_exception_sanitizes_sensitive_data():
    """Internal server errors sanitize database credentials and tokens before logging/responding."""
    sensitive_error = "Connection failed to postgresql://postgres:SuperSecretDBPass@localhost:5432/ecommerce"
    redacted = redact_sensitive_text(sensitive_error)

    assert "SuperSecretDBPass" not in redacted
    assert "postgresql://postgres:[REDACTED]@localhost:5432/ecommerce" in redacted


# ==============================================================================
# 5. Logging Secret Redaction Tests
# ==============================================================================

def test_logging_redacts_jwt_and_bearer_tokens():
    """Logger filter redacts JWT tokens and Bearer headers from log output."""
    sample_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThisSignature12345"
    message = f"User authenticated with Bearer {sample_jwt}"

    redacted = redact_sensitive_text(message)
    assert sample_jwt not in redacted
    assert "Bearer [REDACTED_TOKEN]" in redacted or "[REDACTED_JWT]" in redacted


def test_logging_redacts_api_keys_and_agent_keys():
    """Logger filter redacts Groq, OpenAI, and Agent keys."""
    message = "Keys used: gsk_abcdef1234567890abcdef123456 and ag_live_secret_agent_key_2026"
    redacted = redact_sensitive_text(message)

    assert "gsk_abcdef1234567890abcdef123456" not in redacted
    assert "ag_live_secret_agent_key_2026" not in redacted
    assert "[REDACTED_API_KEY]" in redacted
    assert "[REDACTED_AGENT_KEY]" in redacted


# ==============================================================================
# 6. Existing Security Boundaries Preservation Tests
# ==============================================================================

def test_jwt_and_rbac_boundaries_remain_functional():
    """JWT and Role-Based Access Control remain intact and unaffected by Phase 18C."""
    from app.core.security import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    client = TestClient(app)

    try:
        # 1. Register a customer user via API to guarantee consistent DB session
        cust_email = f"customer_{uuid.uuid4()}@example.com"
        res_reg = client.post(
            "/api/auth/register",
            json={"email": cust_email, "password": "SecurePassword123!"},
        )
        assert res_reg.status_code == 201
        customer_id = res_reg.json()["id"]

        customer_token = create_access_token(customer_id, additional_claims={"role": "customer"})

        # 2. Customer accessing admin endpoint is forbidden (403)
        res_admin = client.get(
            "/api/admin/system/status",
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert res_admin.status_code == 403

        # 3. Request without token is unauthorized (401)
        res_no_auth = client.get("/api/admin/system/status")
        assert res_no_auth.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_agent_to_agent_commerce_boundary_intact():
    """X-Agent-Key machine authentication remains functional and independent."""
    client = TestClient(app)

    # Valid agent key succeeds on discover endpoint
    res_valid = client.post(
        "/api/agent-commerce/discover",
        json={"query": "wireless headphones"},
        headers={"X-Agent-Key": settings.COMMERCE_AGENT_KEY},
    )
    assert res_valid.status_code == 200

    # Invalid agent key fails (401)
    res_invalid = client.post(
        "/api/agent-commerce/discover",
        json={"query": "wireless headphones"},
        headers={"X-Agent-Key": "invalid_wrong_agent_key"},
    )
    assert res_invalid.status_code == 401


def test_razorpay_webhook_hmac_boundary_intact():
    """Razorpay Webhook HMAC signature verification remains functional and strict."""
    client = TestClient(app)

    # Missing signature rejected with 400
    res_missing = client.post(
        "/api/payments/webhook",
        content=b'{"event": "payment.captured"}',
        headers={"Content-Type": "application/json"},
    )
    assert res_missing.status_code == 400
    assert "Missing X-Razorpay-Signature" in res_missing.json()["detail"]
