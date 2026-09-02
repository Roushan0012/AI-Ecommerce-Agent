import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

# Argon2id password hasher with secure defaults
_password_hasher = PasswordHasher()


class JWTError(Exception):
    """Base exception for JWT verification errors."""
    pass


class ExpiredTokenError(JWTError):
    """Raised when an access token has passed its expiration time."""
    pass


class InvalidTokenError(JWTError):
    """Raised when an access token is malformed, has an invalid signature, or is missing required claims."""
    pass


# ==============================================================================
# 1. Password Hashing & Verification (Argon2id)
# ==============================================================================

def hash_password(password: str) -> str:
    """
    Hashes a plaintext password using Argon2id algorithm.
    Never stores or logs plaintext passwords.
    """
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string.")
    return _password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against an Argon2id hashed password string.
    Returns True if valid, False on mismatch, invalid hash format, or empty values.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return _password_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    except Exception as e:
        logger.error(f"Unexpected error during password verification: {type(e).__name__}")
        return False


# ==============================================================================
# 2. JWT Access Token Creation & Cryptographic Verification
# ==============================================================================

def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Creates a signed JWT access token.
    - subject: unique user identifier (e.g. UUID string or email)
    - expires_delta: optional expiration duration (defaults to settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    - additional_claims: optional dictionary of custom claims (core claims take precedence)
    """
    if subject is None or (isinstance(subject, str) and not subject.strip()):
        raise ValueError("Token subject ('sub') cannot be empty.")

    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "nbf": int(now.timestamp()),
    }

    if additional_claims:
        for key, value in additional_claims.items():
            if key not in ["sub", "iat", "exp", "nbf"]:
                payload[key] = value

    secret_key = settings.JWT_SECRET_KEY
    if not secret_key:
        raise ValueError("JWT_SECRET_KEY is not configured.")

    algorithm = settings.JWT_ALGORITHM or "HS256"
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_access_token(
    token: str,
    secret_key: Optional[str] = None,
    algorithm: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Decodes and cryptographically verifies a JWT access token.
    Validates:
    - Cryptographic signature against configured secret_key and algorithm
    - Token expiration ('exp')
    - Token issued-at ('iat') and not-before ('nbf')
    - Subject presence ('sub')
    
    Raises:
    - ExpiredTokenError if token has expired
    - InvalidTokenError if token signature is invalid, malformed, or missing required claims
    """
    if not token or not isinstance(token, str) or not token.strip():
        raise InvalidTokenError("Access token cannot be empty.")

    secret = secret_key or settings.JWT_SECRET_KEY
    if not secret:
        raise ValueError("JWT_SECRET_KEY is not configured.")

    algo = algorithm or settings.JWT_ALGORITHM or "HS256"

    try:
        payload = jwt.decode(
            token.strip(),
            secret,
            algorithms=[algo],
            options={
                "require": ["sub", "exp", "iat"],
                "verify_exp": True,
                "verify_iat": True,
            },
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        raise ExpiredTokenError("Access token has expired.") from e
    except (jwt.InvalidSignatureError, jwt.DecodeError, jwt.InvalidTokenError) as e:
        raise InvalidTokenError(f"Invalid access token: {type(e).__name__}") from e
    except Exception as e:
        raise InvalidTokenError(f"Access token verification failed: {type(e).__name__}") from e


# ==============================================================================
# 3. JWT Authentication Dependency (FastAPI)
# ==============================================================================

def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency for authenticating user requests via Bearer JWT.
    - Reads Authorization header
    - Enforces Bearer scheme
    - Cryptographically verifies signature and expiration
    - Extracts subject UUID
    - Looks up User in database
    - Rejects missing, invalid, expired, nonexistent, or inactive credentials with 401
    """
    if not authorization or not authorization.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme. Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1].strip()

    try:
        payload = decode_access_token(token)
    except ExpiredTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (InvalidTokenError, JWTError, Exception) as exc:
        logger.warning(f"JWT verification failed: {type(exc).__name__}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token: missing subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(str(sub))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject format.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"JWT subject not found in database: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning(f"Inactive user attempted API access: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or disabled.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user

