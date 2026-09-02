import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory if it exists
backend_dir = Path(__file__).resolve().parent.parent.parent
env_file = backend_dir / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file, override=True)
else:
    load_dotenv(override=True)


class Settings:
    @property
    def DATABASE_URL(self) -> str:
        return os.getenv("DATABASE_URL", "")

    @property
    def SUPABASE_URL(self) -> str:
        return os.getenv("SUPABASE_URL", "")

    @property
    def SUPABASE_PUBLISHABLE_KEY(self) -> str:
        return os.getenv("SUPABASE_PUBLISHABLE_KEY", "")

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

    # Razorpay Configuration (Test Mode)
    @property
    def RAZORPAY_KEY_ID(self) -> str:
        return os.getenv("RAZORPAY_KEY_ID", "rzp_test_placeholder")

    @property
    def RAZORPAY_KEY_SECRET(self) -> str:
        return os.getenv("RAZORPAY_KEY_SECRET", "")

    @property
    def RAZORPAY_CURRENCY(self) -> str:
        return os.getenv("RAZORPAY_CURRENCY", "INR")

    @property
    def RAZORPAY_WEBHOOK_SECRET(self) -> str:
        return os.getenv("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret_key_123")

    # Agent-to-Agent Commerce Configuration (Phase 15)
    @property
    def COMMERCE_AGENT_KEY(self) -> str:
        return os.getenv("COMMERCE_AGENT_KEY", "ag_live_key_test_commerce_2026")

    # JWT Authentication Configuration (Phase 17A)
    @property
    def JWT_SECRET_KEY(self) -> str:
        return os.getenv("JWT_SECRET_KEY", "dev_jwt_secret_key_change_in_production_min_32_chars")

    @property
    def JWT_ALGORITHM(self) -> str:
        return os.getenv("JWT_ALGORITHM", "HS256")

    @property
    def JWT_ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        try:
            return int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        except ValueError:
            return 60

    def get_database_url(self) -> str:
        url = self.DATABASE_URL
        if not url:
            raise ValueError(
                "DATABASE_URL environment variable is missing. Please configure DATABASE_URL in your .env file."
            )
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url


settings = Settings()
