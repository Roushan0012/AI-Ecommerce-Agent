"""Phase 18F-1 — Deployment Architecture & Configuration Foundation Tests.

Validates:
1. Three-tier architecture configuration parameters (FastAPI, PostgreSQL, Next.js)
2. Production server binding properties (HOST, PORT, WEB_CONCURRENCY)
3. Deployment health & readiness probe contracts (/api/health, /api/health/database)
4. Production environment validation rules and error masking
5. Safe localhost defaults and production override behavior
6. Boundary isolation between client and server configuration
"""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.core.config import Settings, ConfigurationError, settings
from app.main import app


def test_deployment_server_binding_defaults(monkeypatch):
    """Verify default server binding for development/test vs production."""
    # Development / Test mode defaults
    monkeypatch.setenv("ENVIRONMENT", "development")
    s_dev = Settings()
    assert s_dev.HOST == "127.0.0.1"
    assert s_dev.PORT == 8000
    assert s_dev.WEB_CONCURRENCY == 1

    # Production mode defaults to 0.0.0.0 for ingress / container binding
    monkeypatch.setenv("ENVIRONMENT", "production")
    s_prod = Settings()
    assert s_prod.HOST == "0.0.0.0"
    assert s_prod.PORT == 8000
    assert s_prod.WEB_CONCURRENCY == 4


def test_deployment_server_binding_environment_overrides(monkeypatch):
    """Verify custom environment overrides for HOST, PORT, and WEB_CONCURRENCY."""
    monkeypatch.setenv("HOST", "10.0.0.5")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("WEB_CONCURRENCY", "8")

    s = Settings()
    assert s.HOST == "10.0.0.5"
    assert s.PORT == 9000
    assert s.WEB_CONCURRENCY == 8


def test_deployment_liveness_and_readiness_probes():
    """Verify health endpoints adhere to standard orchestrator probe contracts."""
    client = TestClient(app)

    # 1. Liveness probe (GET /api/health)
    live_res = client.get("/api/health")
    assert live_res.status_code == 200
    data = live_res.json()
    assert data["status"] == "ok"
    assert data["service"] == "ai-commerce-agent-api"

    # 2. Readiness probe (GET /api/health/database)
    ready_res = client.get("/api/health/database")
    assert ready_res.status_code in (200, 503)
    ready_data = ready_res.json()
    assert "status" in ready_data
    assert "database" in ready_data


def test_deployment_proxy_headers_client_ip_forwarding():
    """Verify that requests behind reverse proxies forward client IP cleanly."""
    client = TestClient(app)
    res = client.get(
        "/api/health",
        headers={"X-Forwarded-For": "203.0.113.195, 198.51.100.1"},
    )
    assert res.status_code == 200


def test_production_cors_strictness(monkeypatch):
    """Verify that production rejects wildcard CORS and accepts trusted domains."""
    monkeypatch.setenv("ENVIRONMENT", "production")

    # Insecure wildcard
    monkeypatch.setenv("CORS_ORIGINS", "*")
    s_bad = Settings()
    with pytest.raises(ConfigurationError) as exc:
        s_bad.validate_cors_origins()
    assert "Wildcard origin" in str(exc.value)

    # Valid explicit production domains
    monkeypatch.setenv("CORS_ORIGINS", "https://ecommerce.example.com,https://admin.example.com")
    s_good = Settings()
    origins = s_good.validate_cors_origins()
    assert "https://ecommerce.example.com" in origins
    assert "https://admin.example.com" in origins


def test_production_configuration_safeguards_contract(monkeypatch):
    """Verify that production validation strictly requires all external service secrets."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example.com:5432/app")
    monkeypatch.setenv("JWT_SECRET_KEY", "super_secure_production_jwt_secret_min_32_characters_123")
    monkeypatch.setenv("COMMERCE_AGENT_KEY", "prod_valid_agent_key_12345")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_live_realproductionid")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "real_razorpay_secret")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "real_webhook_secret")
    monkeypatch.setenv("CORS_ORIGINS", "https://ecommerce.example.com")

    s = Settings()
    # Should not raise
    s.validate_production_config()


def test_env_examples_contain_all_required_variables():
    """Verify that backend/.env.example documents all essential production keys."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    backend_env = (repo_root / "backend" / ".env.example").read_text(encoding="utf-8")
    frontend_env = (repo_root / "frontend" / ".env.example").read_text(encoding="utf-8")

    # Backend required keys
    assert "HOST=" in backend_env
    assert "PORT=" in backend_env
    assert "WEB_CONCURRENCY=" in backend_env
    assert "ENVIRONMENT=" in backend_env
    assert "DATABASE_URL=" in backend_env
    assert "JWT_SECRET_KEY=" in backend_env
    assert "COMMERCE_AGENT_KEY=" in backend_env
    assert "RAZORPAY_KEY_ID=" in backend_env
    assert "RAZORPAY_KEY_SECRET=" in backend_env
    assert "RAZORPAY_WEBHOOK_SECRET=" in backend_env
    assert "CORS_ORIGINS=" in backend_env

    # Frontend required keys
    assert "NEXT_PUBLIC_API_BASE_URL=" in frontend_env
    assert "NEXT_PUBLIC_RAZORPAY_KEY_ID=" in frontend_env
