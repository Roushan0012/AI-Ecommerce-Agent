import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.auth import Token, UserLoginRequest, UserRegisterRequest, UserResponse
from app.services.auth_service import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user account",
    description="Validates email format and password strength, hashes password with Argon2id, and creates user account.",
)
def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Register a new user account with unique email and hashed password."""
    user = auth_service.register_user(db=db, request=request)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and issue JWT access token",
    description="Verifies user credentials and returns a signed JWT access token with the user UUID as subject.",
)
def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db),
) -> Token:
    """Authenticate user with email and password to receive JWT access token."""
    return auth_service.authenticate_user(db=db, request=request)
