"""
Phase 18A — Production Configuration Foundation Tests

Covers:
- Development configuration loads correctly
- Test configuration remains compatible with existing tests
- Production configuration accepts valid environment variables
- Production configuration rejects missing critical secrets/configuration
- Production debug mode is strictly disabled
- CORS origins are configurable (comma-separated and JSON list)
- Wildcard production CORS is rejected when unsafe
- Existing JWT configuration remains functional
- Existing X-Agent-Key configuration remains functional
- Existing Razorpay configuration remains functional
- No secrets appear in error messages
- Production error responses do not leak internal stack traces
"""

import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.config import Settings, ConfigurationError, settings
from app.main import app


# ==============================================================================
# 1. Environment and Defaults
# ==============================================================================

def test_development_configuration_defaults(monkeypatch):
    """1.1 Development environment loads safe local defaults."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    s = Settings()
    assert s.ENVIRONMENT == "development"
    assert s.is_development is True
    assert s.is_production is False
    assert s.is_test is False
    assert s.DEBUG is True
    assert "http://localhost:3000" in s.CORS_ORIGINS
    assert "http://127.0.0.1:3000" in s.CORS_ORIGINS


def test_test_configuration_compatibility(monkeypatch):
    """1.2 Test environment remains compatible with test suite."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.delenv("COMMERCE_AGENT_KEY", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_WEBHOOK_SECRET", raising=False)
    s = Settings()
    assert s.ENVIRONMENT == "test"
    assert s.is_test is True
    assert s.is_production is False
    assert s.COMMERCE_AGENT_KEY == "ag_live_key_test_commerce_2026"
    assert s.RAZORPAY_KEY_ID == "rzp_test_placeholder"
    assert s.RAZORPAY_WEBHOOK_SECRET == "test_webhook_secret_key_123"


# ==============================================================================
# 2. Production Configuration Acceptance & Validation
# ==============================================================================

def test_production_configuration_accepts_valid_environment(monkeypatch):
    """2.1 Production configuration accepts complete, valid production environment variables."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://prod_usr:strong_secret@db.supabase.co:5432/postgres")
    monkeypatch.setenv("JWT_SECRET_KEY", "super_strong_production_jwt_secret_min_32_characters_long!")
    monkeypatch.setenv("COMMERCE_AGENT_KEY", "prod_agent_key_min_16_chars_secure_99")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_mock_live_id_123456789")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "mock_rzp_prod_test_secret_key_123")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "mock_rzp_webhook_secret_secure_99")
    monkeypatch.setenv("CORS_ORIGINS", "https://shop.example.com,https://admin.example.com")

    s = Settings()
    assert s.is_production is True
    # Validation must succeed without raising ConfigurationError
    s.validate_production_config()


def test_production_configuration_rejects_missing_database_url(monkeypatch):
    """2.2 Production configuration fails when DATABASE_URL is missing."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("JWT_SECRET_KEY", "super_strong_production_jwt_secret_min_32_characters_long!")
    monkeypatch.setenv("COMMERCE_AGENT_KEY", "prod_agent_key_min_16_chars_secure_99")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_mock_live_id_123456789")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "mock_rzp_prod_test_secret_key_123")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "mock_rzp_webhook_secret_secure_99")

    s = Settings()
    with pytest.raises(ConfigurationError) as exc_info:
        s.validate_production_config()
    assert "DATABASE_URL" in str(exc_info.value)


def test_production_configuration_rejects_sqlite_in_production(monkeypatch):
    """2.3 Production configuration rejects SQLite database URL."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("JWT_SECRET_KEY", "super_strong_production_jwt_secret_min_32_characters_long!")
    monkeypatch.setenv("COMMERCE_AGENT_KEY", "prod_agent_key_min_16_chars_secure_99")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_mock_live_id_123456789")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "mock_rzp_prod_test_secret_key_123")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "mock_rzp_webhook_secret_secure_99")

    s = Settings()
    with pytest.raises(ConfigurationError) as exc_info:
        s.validate_production_config()
    assert "SQLite is not permitted in production" in str(exc_info.value)


def test_production_configuration_rejects_insecure_jwt_secret(monkeypatch):
    """2.4 Production configuration rejects missing or default development JWT secret."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example.com:5432/prod")
    monkeypatch.setenv("JWT_SECRET_KEY", "dev_jwt_secret_key_change_in_production_min_32_chars")
    monkeypatch.setenv("COMMERCE_AGENT_KEY", "prod_agent_key_min_16_chars_secure_99")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_mock_live_id_123456789")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "mock_rzp_prod_test_secret_key_123")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "mock_rzp_webhook_secret_secure_99")

    s = Settings()
    with pytest.raises(ConfigurationError) as exc_info:
        s.validate_production_config()
    assert "JWT_SECRET_KEY" in str(exc_info.value)


def test_production_configuration_rejects_insecure_agent_key(monkeypatch):
    """2.5 Production configuration rejects default development agent key."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example.com:5432/prod")
    monkeypatch.setenv("JWT_SECRET_KEY", "super_strong_production_jwt_secret_min_32_characters_long!")
    monkeypatch.setenv("COMMERCE_AGENT_KEY", "ag_live_key_test_commerce_2026")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_mock_live_id_123456789")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "mock_rzp_prod_test_secret_key_123")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "mock_rzp_webhook_secret_secure_99")

    s = Settings()
    with pytest.raises(ConfigurationError) as exc_info:
        s.validate_production_config()
    assert "COMMERCE_AGENT_KEY" in str(exc_info.value)


def test_production_configuration_rejects_insecure_razorpay_credentials(monkeypatch):
    """2.6 Production configuration rejects missing or placeholder Razorpay credentials."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example.com:5432/prod")
    monkeypatch.setenv("JWT_SECRET_KEY", "super_strong_production_jwt_secret_min_32_characters_long!")
    monkeypatch.setenv("COMMERCE_AGENT_KEY", "prod_agent_key_min_16_chars_secure_99")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_placeholder")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret_key_123")

    s = Settings()
    with pytest.raises(ConfigurationError) as exc_info:
        s.validate_production_config()
    err = str(exc_info.value)
    assert "RAZORPAY_KEY_ID" in err
    assert "RAZORPAY_KEY_SECRET" in err
    assert "RAZORPAY_WEBHOOK_SECRET" in err


# ==============================================================================
# 3. Debug Separation & Production Hardening
# ==============================================================================

def test_production_debug_mode_strictly_disabled(monkeypatch):
    """3.1 Production mode enforces DEBUG=False regardless of environment flag."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "true")

    s = Settings()
    assert s.DEBUG is False

    monkeypatch.setenv("DEBUG", "1")
    assert s.DEBUG is False


def test_development_debug_mode_configurable(monkeypatch):
    """3.2 Development mode permits configurable DEBUG mode."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEBUG", "true")
    assert Settings().DEBUG is True

    monkeypatch.setenv("DEBUG", "false")
    assert Settings().DEBUG is False


# ==============================================================================
# 4. CORS Configuration
# ==============================================================================

def test_cors_origins_configurable_comma_separated(monkeypatch):
    """4.1 CORS origins load from comma-separated string."""
    monkeypatch.setenv("CORS_ORIGINS", "https://shop.example.com, https://admin.example.com")
    s = Settings()
    assert s.CORS_ORIGINS == ["https://shop.example.com", "https://admin.example.com"]


def test_cors_origins_configurable_json_array(monkeypatch):
    """4.2 CORS origins load from JSON array string."""
    monkeypatch.setenv("CORS_ORIGINS", '["https://shop.example.com", "https://admin.example.com"]')
    s = Settings()
    assert s.CORS_ORIGINS == ["https://shop.example.com", "https://admin.example.com"]


def test_wildcard_production_cors_is_rejected(monkeypatch):
    """4.3 Insecure wildcard origin '*' in production is strictly rejected."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "*")

    s = Settings()
    with pytest.raises(ConfigurationError) as exc_info:
        s.validate_cors_origins()
    assert "Wildcard origin '*'" in str(exc_info.value)


def test_wildcard_mixed_production_cors_is_rejected(monkeypatch):
    """4.4 Insecure wildcard origin '*' combined with domains in production is strictly rejected."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://shop.example.com,*")

    s = Settings()
    with pytest.raises(ConfigurationError) as exc_info:
        s.validate_cors_origins()
    assert "Wildcard origin '*'" in str(exc_info.value)


# ==============================================================================
# 5. Non-Exposure of Secrets in Errors and Production Responses
# ==============================================================================

def test_no_secrets_appear_in_error_messages(monkeypatch):
    """5.1 Configuration validation error messages list variable names and never leak secret values."""
    real_secret_value = "super_classified_secret_key_value_98765"
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("JWT_SECRET_KEY", real_secret_value[:10])  # too short
    monkeypatch.setenv("COMMERCE_AGENT_KEY", "")

    s = Settings()
    with pytest.raises(ConfigurationError) as exc_info:
        s.validate_production_config()

    err_message = str(exc_info.value)
    # The error message should describe what is missing
    assert "JWT_SECRET_KEY" in err_message
    assert "DATABASE_URL" in err_message
    # But MUST NOT print the secret value itself
    assert real_secret_value[:10] not in err_message


def test_production_error_responses_mask_internal_exceptions(monkeypatch):
    """5.2 Production unhandled exception handler masks stack traces and internal messages."""
    monkeypatch.setenv("ENVIRONMENT", "production")

    test_app = FastAPI()

    # Add error route that throws internal exception with simulated sensitive detail
    @test_app.get("/error-test")
    def trigger_error():
        raise RuntimeError("Database connection string postgresql://secret:pass@host/db failed")

    # Attach the same unhandled exception handler as app.main
    from app.main import unhandled_exception_handler
    test_app.add_exception_handler(Exception, unhandled_exception_handler)

    client = TestClient(test_app, raise_server_exceptions=False)
    res = client.get("/error-test")
    assert res.status_code == 500
    data = res.json()
    assert data["detail"] == "An internal server error occurred. Please contact support."
    assert "postgresql" not in str(data)
    assert "secret" not in str(data)
    assert "traceback" not in str(data).lower()


# ==============================================================================
# 6. Backward Compatibility for Existing Systems
# ==============================================================================

def test_existing_jwt_configuration_remains_functional():
    """6.1 Existing JWT settings properties remain functional and well-typed."""
    assert isinstance(settings.JWT_SECRET_KEY, str)
    assert settings.JWT_ALGORITHM == "HS256"
    assert isinstance(settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES, int)
    assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 0


def test_existing_agent_commerce_key_configuration_remains_functional():
    """6.2 Existing Agent Commerce Key property remains functional."""
    assert isinstance(settings.COMMERCE_AGENT_KEY, str)
    assert len(settings.COMMERCE_AGENT_KEY) > 0


def test_existing_razorpay_configuration_remains_functional():
    """6.3 Existing Razorpay configuration properties remain functional."""
    assert isinstance(settings.RAZORPAY_KEY_ID, str)
    assert isinstance(settings.RAZORPAY_CURRENCY, str)
    assert settings.RAZORPAY_CURRENCY == "INR"
    assert isinstance(settings.RAZORPAY_WEBHOOK_SECRET, str)
