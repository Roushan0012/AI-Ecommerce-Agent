import re
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class UserRegisterRequest(BaseModel):
    """Schema for user registration request."""
    email: str = Field(..., description="User email address", min_length=3, max_length=255)
    password: str = Field(..., description="User password (min 8 characters)", min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_and_normalize_email(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("Email cannot be empty.")
        normalized = v.strip().lower()
        if not EMAIL_REGEX.match(normalized):
            raise ValueError("Invalid email format.")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("Password cannot be empty.")
        if len(v.strip()) < 8:
            raise ValueError("Password must be at least 8 characters long and cannot consist only of whitespace.")
        return v


class UserLoginRequest(BaseModel):
    """Schema for user login request."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("Email cannot be empty.")
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password_present(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("Password cannot be empty.")
        return v


class UserResponse(BaseModel):
    """Safe user profile response (omits password and password_hash)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique user UUID")
    email: str = Field(..., description="Normalized user email")
    is_active: bool = Field(..., description="Whether user account is active")
    created_at: datetime = Field(..., description="Account creation UTC timestamp")
    updated_at: datetime = Field(..., description="Account last update UTC timestamp")


class Token(BaseModel):
    """Schema representing an issued JWT token response."""
    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(..., description="JWT access token string")
    token_type: str = Field("bearer", description="Token type header prefix (typically Bearer)")
    expires_in: Optional[int] = Field(None, description="Token expiration duration in seconds")


class TokenPayload(BaseModel):
    """Schema representing decoded JWT claims."""
    model_config = ConfigDict(from_attributes=True)

    sub: str = Field(..., description="Subject identifier (user UUID or email)")
    exp: int = Field(..., description="Expiration UTC timestamp in epoch seconds")
    iat: int = Field(..., description="Issued at UTC timestamp in epoch seconds")
    nbf: Optional[int] = Field(None, description="Not before UTC timestamp in epoch seconds")
