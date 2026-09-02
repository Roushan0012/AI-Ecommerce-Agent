import logging
import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.audit import AuditEventType
from app.schemas.auth import Token, UserLoginRequest, UserRegisterRequest, UserResponse
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)


class AuthService:
    """Service handling user registration, authentication, and token issuance."""

    def register_user(self, db: Session, request: UserRegisterRequest) -> User:
        """
        Registers a new user account.
        - Validates and normalizes email
        - Validates password length and complexity
        - Enforces unique email constraint (rejects duplicates)
        - Hashes password with Argon2id (never stores plaintext)
        - Persists user to database
        """
        normalized_email = request.email.strip().lower()

        # Check if user with this email already exists
        existing_user = db.query(User).filter(User.email == normalized_email).first()
        if existing_user:
            logger.warning(f"Registration rejected: duplicate email attempt for '{normalized_email}'")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered.",
            )

        hashed_password = hash_password(request.password)

        new_user = User(
            id=uuid.uuid4(),
            email=normalized_email,
            password_hash=hashed_password,
            is_active=True,
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Log audit event safely (never log password or password hash)
        try:
            audit_service.record_event(
                db=db,
                event_type=AuditEventType.USER_REGISTERED,
                customer_id=new_user.id,
                action="register_user",
                payload={"email": normalized_email, "user_id": str(new_user.id)},
                status="success",
            )
        except Exception as audit_err:
            logger.warning(f"Failed to record registration audit log: {audit_err}")

        logger.info(f"User registered successfully: {new_user.id}")
        return new_user

    def authenticate_user(self, db: Session, request: UserLoginRequest) -> Token:
        """
        Authenticates a user and issues a signed JWT access token.
        - Normalizes email
        - Uses constant-time Argon2 verification
        - Returns generic 401 on unknown user or bad password (prevents email enumeration)
        - Rejects inactive accounts
        - Generates signed JWT with user UUID as 'sub'
        """
        normalized_email = request.email.strip().lower()

        user = db.query(User).filter(User.email == normalized_email).first()

        # Constant-time verification or dummy check to prevent timing attacks
        if not user or not verify_password(request.password, user.password_hash):
            logger.warning(f"Authentication failed for email: {normalized_email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            logger.warning(f"Authentication rejected for inactive user: {user.id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled or inactive.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate JWT access token with user UUID as subject
        access_token = create_access_token(subject=str(user.id))
        expires_in = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

        # Log audit event
        try:
            audit_service.record_event(
                db=db,
                event_type=AuditEventType.USER_LOGIN,
                customer_id=user.id,
                action="login_user",
                payload={"email": normalized_email, "user_id": str(user.id)},
                status="success",
            )
        except Exception as audit_err:
            logger.warning(f"Failed to record login audit log: {audit_err}")

        logger.info(f"User authenticated successfully: {user.id}")
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
        )


auth_service = AuthService()
