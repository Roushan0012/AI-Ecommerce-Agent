from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


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
