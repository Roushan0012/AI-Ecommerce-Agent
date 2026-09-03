import json
import os
import sys
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load .env from backend directory if it exists
backend_dir = Path(__file__).resolve().parent.parent.parent
env_file = backend_dir / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file, override=True)
else:
    load_dotenv(override=True)


class ConfigurationError(ValueError):
    """Raised when environment or production security configuration is invalid."""
    pass


class Settings:
    # Known insecure dev/test placeholders that MUST NOT be used in production
    INSECURE_DEV_JWT_SECRET = "dev_jwt_secret_key_change_in_production_min_32_chars"
    INSECURE_DEV_AGENT_KEY = "ag_live_key_test_commerce_2026"
    INSECURE_DEV_AGENT_KEY_PLACEHOLDER = "ag_live_key_placeholder"
    INSECURE_DEV_RAZORPAY_KEY_ID = "rzp_test_placeholder"
    INSECURE_DEV_RAZORPAY_WEBHOOK_SECRET = "test_webhook_secret_key_123"

    # Environment
    @property
    def ENVIRONMENT(self) -> str:
        env = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "")).lower().strip()
        if env in ("development", "test", "production"):
            return env
        if "pytest" in sys.modules or os.getenv("PYTEST_CURRENT_TEST"):
            return "test"
        return "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_test(self) -> bool:
        return self.ENVIRONMENT == "test"

    @property
    def DEBUG(self) -> bool:
        # Debug is strictly disabled in production
        if self.is_production:
            return False
        val = os.getenv("DEBUG", "true" if self.is_development else "false").lower().strip()
        return val in ("true", "1", "yes", "t")

    # CORS Configuration
    @property
    def CORS_ORIGINS(self) -> List[str]:
        raw = os.getenv("CORS_ORIGINS", "")
        if raw:
            raw = raw.strip()
            if raw.startswith("[") and raw.endswith("]"):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if item]
                except Exception:
                    pass
            return [origin.strip() for origin in raw.split(",") if origin.strip()]
        # Safe default development & test origins
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

    def validate_cors_origins(self) -> List[str]:
        origins = self.CORS_ORIGINS
        if self.is_production:
            if not origins:
                raise ConfigurationError(
                    "Production CORS misconfiguration: CORS_ORIGINS must specify at least one trusted domain."
                )
            if "*" in origins:
                raise ConfigurationError(
                    "Insecure CORS configuration: Wildcard origin '*' is forbidden in production when credentials are enabled."
                )
        return origins

    # Database
    @property
    def DATABASE_URL(self) -> str:
        return os.getenv("DATABASE_URL", "")

    @property
    def SUPABASE_URL(self) -> str:
        return os.getenv("SUPABASE_URL", "")

    @property
    def SUPABASE_PUBLISHABLE_KEY(self) -> str:
        return os.getenv("SUPABASE_PUBLISHABLE_KEY", "")

    def get_database_url(self) -> str:
        url = self.DATABASE_URL
        if not url:
            raise ValueError(
                "DATABASE_URL environment variable is missing. Please configure DATABASE_URL in your .env file."
            )
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    # AI Configuration
    @property
    def AI_PROVIDER(self) -> str:
        return os.getenv("AI_PROVIDER", "mock").lower()

    @property
    def AI_MODEL(self) -> str:
        return os.getenv("AI_MODEL", "gpt-4o-mini")

    @property
    def AI_API_KEY(self) -> str:
        return os.getenv("AI_API_KEY", "")

    @property
    def AI_BASE_URL(self) -> str:
        return os.getenv("AI_BASE_URL", "")

    # Razorpay Configuration (Test Mode safe defaults in dev/test)
    @property
    def RAZORPAY_KEY_ID(self) -> str:
        return os.getenv("RAZORPAY_KEY_ID", "rzp_test_placeholder" if not self.is_production else "")

    @property
    def RAZORPAY_KEY_SECRET(self) -> str:
        return os.getenv("RAZORPAY_KEY_SECRET", "")

    @property
    def RAZORPAY_CURRENCY(self) -> str:
        return os.getenv("RAZORPAY_CURRENCY", "INR")

    @property
    def RAZORPAY_WEBHOOK_SECRET(self) -> str:
        return os.getenv(
            "RAZORPAY_WEBHOOK_SECRET",
            "test_webhook_secret_key_123" if not self.is_production else "",
        )

    # Agent-to-Agent Commerce Configuration (Phase 15)
    @property
    def COMMERCE_AGENT_KEY(self) -> str:
        return os.getenv(
            "COMMERCE_AGENT_KEY",
            "ag_live_key_test_commerce_2026" if not self.is_production else "",
        )

    # JWT Authentication Configuration (Phase 17A)
    @property
    def JWT_SECRET_KEY(self) -> str:
        return os.getenv(
            "JWT_SECRET_KEY",
            "dev_jwt_secret_key_change_in_production_min_32_chars" if not self.is_production else "",
        )

    @property
    def JWT_ALGORITHM(self) -> str:
        return os.getenv("JWT_ALGORITHM", "HS256")

    @property
    def JWT_ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        try:
            return int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        except ValueError:
            return 60

    # Phase 18C - Rate Limiting & Request Hardening Configuration
    @property
    def RATE_LIMIT_ENABLED(self) -> bool:
        val = os.getenv("RATE_LIMIT_ENABLED", "true").lower().strip()
        return val in ("true", "1", "yes", "t")

    @property
    def RATE_LIMIT_AUTH_PER_MINUTE(self) -> int:
        raw = os.getenv("RATE_LIMIT_AUTH_PER_MINUTE")
        if raw:
            try:
                return max(1, int(raw))
            except ValueError:
                pass
        return 1000 if self.is_test else (10 if self.is_production else 30)

    @property
    def RATE_LIMIT_DEFAULT_PER_MINUTE(self) -> int:
        raw = os.getenv("RATE_LIMIT_DEFAULT_PER_MINUTE")
        if raw:
            try:
                return max(1, int(raw))
            except ValueError:
                pass
        return 10000 if self.is_test else (120 if self.is_production else 300)

    @property
    def MAX_REQUEST_BODY_BYTES(self) -> int:
        raw = os.getenv("MAX_REQUEST_BODY_BYTES")
        if raw:
            try:
                return max(1, int(raw))
            except ValueError:
                pass
        return 2 * 1024 * 1024  # 2MB default

    @property
    def SECURITY_HEADERS_ENABLED(self) -> bool:
        val = os.getenv("SECURITY_HEADERS_ENABLED", "true").lower().strip()
        return val in ("true", "1", "yes", "t")

    # Production Configuration Validation
    def validate_production_config(self) -> None:
        """
        Validates that all critical production configuration and secret parameters are explicitly provided
        and not using insecure development defaults.

        Raises ConfigurationError listing missing variable names.
        Never prints or exposes secret values.
        """
        missing_or_insecure = []

        # 1. Database
        db_url = self.DATABASE_URL.strip()
        if not db_url:
            missing_or_insecure.append("DATABASE_URL (missing)")
        elif "sqlite" in db_url.lower():
            missing_or_insecure.append("DATABASE_URL (SQLite is not permitted in production)")

        # 2. JWT Secret
        jwt_secret = os.getenv("JWT_SECRET_KEY", "").strip()
        if not jwt_secret or jwt_secret == self.INSECURE_DEV_JWT_SECRET or len(jwt_secret) < 32:
            missing_or_insecure.append("JWT_SECRET_KEY (must be set with at least 32 characters)")

        # 3. Commerce Agent Key
        agent_key = os.getenv("COMMERCE_AGENT_KEY", "").strip()
        if (
            not agent_key
            or agent_key in (self.INSECURE_DEV_AGENT_KEY, self.INSECURE_DEV_AGENT_KEY_PLACEHOLDER)
            or len(agent_key) < 16
        ):
            missing_or_insecure.append("COMMERCE_AGENT_KEY (must be set with at least 16 characters)")

        # 4. Razorpay Credentials
        rzp_key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
        if not rzp_key_id or rzp_key_id == self.INSECURE_DEV_RAZORPAY_KEY_ID:
            missing_or_insecure.append("RAZORPAY_KEY_ID (must be configured with production key)")

        rzp_key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
        if not rzp_key_secret:
            missing_or_insecure.append("RAZORPAY_KEY_SECRET (missing)")

        rzp_webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()
        if not rzp_webhook_secret or rzp_webhook_secret == self.INSECURE_DEV_RAZORPAY_WEBHOOK_SECRET:
            missing_or_insecure.append("RAZORPAY_WEBHOOK_SECRET (must be configured with production webhook secret)")

        # 5. CORS Origins
        try:
            self.validate_cors_origins()
        except ConfigurationError as e:
            missing_or_insecure.append(f"CORS_ORIGINS ({str(e)})")

        if missing_or_insecure:
            raise ConfigurationError(
                f"Production configuration validation failed. Critical parameters missing or insecure: {missing_or_insecure}."
            )


settings = Settings()
