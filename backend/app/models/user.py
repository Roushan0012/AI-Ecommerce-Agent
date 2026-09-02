from enum import Enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, validates
from app.core.database import Base


class UserRole(str, Enum):
    """Controlled set of authorization roles in the AI Commerce platform."""
    CUSTOMER = "customer"
    MERCHANT = "merchant"
    ADMIN = "admin"

    @classmethod
    def values(cls) -> set[str]:
        return {r.value for r in cls}

    @classmethod
    def is_valid(cls, role: str) -> bool:
        return role in cls.values()


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(50), default=UserRole.CUSTOMER.value, nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False
    )

    @validates("role")
    def validate_role(self, key: str, role: str) -> str:
        """Validates that user role belongs to the controlled UserRole set."""
        if not role or role not in UserRole.values():
            raise ValueError(
                f"Invalid user role '{role}'. Allowed roles are: {sorted(UserRole.values())}"
            )
        return role

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}', is_active={self.is_active})>"
