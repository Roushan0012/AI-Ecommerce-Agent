"""Phase 18F-2 — Backend Deployment Readiness Tests.

Validates:
1. Production PostgreSQL/Supabase database readiness and prevention of silent SQLite fallback
2. Health and readiness endpoints isolation (/api/health, /api/health/database)
3. Zero sensitive data disclosure on probe failure or database errors
4. Production startup configuration validation safeguards
5. Backend Dockerfile syntax, non-root user execution, and healthcheck configuration
6. Dockerignore secret and artifact exclusion
"""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.core.config import Settings, ConfigurationError
from app.core import database
from app.main import app


def test_production_blocks_silent_sqlite_fallback(monkeypatch):
    """Verify that in production mode, failed primary database connection does NOT fall back to SQLite."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@unreachable-host.example.com:5432/db")

    # Reset cached engine
    database._engine = None
    database._SessionLocal = None

    engine = database.get_engine()
    # In production, engine remains the postgresql engine and does NOT switch to SQLite
    assert "sqlite" not in str(engine.url).lower()
    assert str(engine.url).startswith("postgresql")

    # Reset cached engine back to None so other tests run cleanly
    database._engine = None
    database._SessionLocal = None


def test_health_endpoints_distinguish_liveness_and_readiness():
    """Verify /api/health serves liveness and /api/health/database serves readiness."""
    client = TestClient(app)

    # 1. Process liveness
    liveness_res = client.get("/api/health")
    assert liveness_res.status_code == 200
    live_data = liveness_res.json()
    assert live_data["status"] == "ok"
    assert live_data["service"] == "ai-commerce-agent-api"
    # Ensure no secret strings or database paths are present
    assert "url" not in live_data
    assert "secret" not in live_data

    # 2. Database readiness
    readiness_res = client.get("/api/health/database")
    assert readiness_res.status_code in (200, 503)
    ready_data = readiness_res.json()
    assert "status" in ready_data
    assert "database" in ready_data
    # Zero secret or connection string disclosure
    for k, v in ready_data.items():
        assert "postgres://" not in str(v).lower()
        assert "password" not in str(v).lower()


def test_readiness_probe_returns_503_when_database_fails(monkeypatch):
    """Verify /api/health/database returns 503 when connection probe returns False."""
    monkeypatch.setattr("app.main.check_database_connection", lambda: False)
    client = TestClient(app)

    res = client.get("/api/health/database")
    assert res.status_code == 503
    data = res.json()
    assert data["detail"]["status"] == "error"
    assert data["detail"]["database"] == "disconnected"
    assert "postgres" not in str(data).lower()
    assert "password" not in str(data).lower()


def test_production_enforces_debug_false(monkeypatch):
    """Verify DEBUG cannot be enabled in production environment."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "true")

    s = Settings()
    assert s.is_production is True
    assert s.DEBUG is False, "DEBUG must be strictly False in production"


def test_production_validation_blocks_all_unconfigured_secrets(monkeypatch):
    """Verify validate_production_config rejects insecure placeholders."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./invalid_prod.db")
    monkeypatch.setenv("JWT_SECRET_KEY", "dev_jwt_secret_key_change_in_production_min_32_chars")
    monkeypatch.setenv("COMMERCE_AGENT_KEY", "ag_live_key_test_commerce_2026")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_placeholder")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret_key_123")
    monkeypatch.setenv("CORS_ORIGINS", "*")

    s = Settings()
    with pytest.raises(ConfigurationError) as exc_info:
        s.validate_production_config()

    err_msg = str(exc_info.value)
    # Check that each offending field is reported
    assert "DATABASE_URL" in err_msg
    assert "JWT_SECRET_KEY" in err_msg
    assert "COMMERCE_AGENT_KEY" in err_msg
    assert "RAZORPAY_KEY_ID" in err_msg
    assert "RAZORPAY_KEY_SECRET" in err_msg
    assert "RAZORPAY_WEBHOOK_SECRET" in err_msg
    assert "CORS_ORIGINS" in err_msg


def test_backend_dockerfile_configuration():
    """Verify backend Dockerfile exists, uses non-root user, and defines healthcheck."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    dockerfile = repo_root / "backend" / "Dockerfile"
    dockerignore = repo_root / "backend" / ".dockerignore"

    assert dockerfile.exists(), "backend/Dockerfile must exist"
    assert dockerignore.exists(), "backend/.dockerignore must exist"

    df_content = dockerfile.read_text(encoding="utf-8")
    # Security: non-root user execution
    assert "USER appuser" in df_content
    # Entry point with production uvicorn
    assert "uvicorn app.main:app" in df_content
    assert "--proxy-headers" in df_content
    assert "--forwarded-allow-ips" in df_content
    # Healthcheck
    assert "HEALTHCHECK" in df_content
    assert "/api/health" in df_content

    # Dockerignore security exclusions
    di_content = dockerignore.read_text(encoding="utf-8")
    assert ".env" in di_content
    assert ".venv" in di_content
    assert "*.db" in di_content
