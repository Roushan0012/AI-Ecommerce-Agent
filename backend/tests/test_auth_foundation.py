import time
from datetime import timedelta
import jwt
import pytest
from app.core.config import settings
from app.core.security import (
    ExpiredTokenError,
    InvalidTokenError,
    JWTError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.schemas.auth import Token, TokenPayload


# ==============================================================================
# 1. Password Hashing & Verification Tests (Argon2id)
# ==============================================================================

def test_password_hashing_produces_distinct_hash():
    """1. Password hashing produces a non-plaintext, salted Argon2id hash."""
    raw_password = "SecurePassword123!@#"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert isinstance(hashed, str)
    assert len(hashed) > 30
    assert "$argon2id$" in hashed


def test_password_hashing_is_salted_and_unique():
    """2. Hashing the same password twice produces distinct salt/hash outputs."""
    raw_password = "SuperSecretPassword2026"
    hash_1 = hash_password(raw_password)
    hash_2 = hash_password(raw_password)

    assert hash_1 != hash_2
    assert verify_password(raw_password, hash_1) is True
    assert verify_password(raw_password, hash_2) is True


def test_correct_password_verification_succeeds():
    """3. Correct password verifies successfully against the generated hash."""
    raw_password = "CorrectHorseBatteryStaple!"
    hashed = hash_password(raw_password)

    assert verify_password(raw_password, hashed) is True


def test_incorrect_password_verification_fails():
    """4. Incorrect password verification returns False without raising exceptions."""
    raw_password = "MySecretPassword123"
    wrong_password = "WrongPassword456"
    hashed = hash_password(raw_password)

    assert verify_password(wrong_password, hashed) is False


def test_password_hashing_empty_or_invalid_inputs():
    """5. Empty passwords raise ValueError, empty/corrupted verification returns False."""
    with pytest.raises(ValueError):
        hash_password("")

    with pytest.raises(ValueError):
        hash_password(None)  # type: ignore

    assert verify_password("", "$argon2id$v=19$m=65536,t=3,p=4$fakehash") is False
    assert verify_password("some_password", "") is False
    assert verify_password("some_password", "invalid_corrupted_hash_string") is False


# ==============================================================================
# 2. JWT Access Token Creation & Verification Tests
# ==============================================================================

def test_access_token_creation_succeeds():
    """6. Access token creation produces a valid three-part JWT string."""
    subject = "user_uuid_12345678"
    token = create_access_token(subject=subject)

    assert isinstance(token, str)
    parts = token.split(".")
    assert len(parts) == 3


def test_token_contains_expected_subject_and_claims():
    """7. Token payload contains the expected subject, iat, and exp timestamps."""
    subject = "customer_c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c"
    token = create_access_token(subject=subject)

    payload = decode_access_token(token)
    assert payload["sub"] == subject
    assert "iat" in payload
    assert "exp" in payload
    assert payload["exp"] > payload["iat"]


def test_token_custom_expiration_duration():
    """8. Custom expiration delta is accurately reflected in token exp claim."""
    subject = "user_fast_expire"
    custom_delta = timedelta(minutes=15)
    token = create_access_token(subject=subject, expires_delta=custom_delta)

    payload = decode_access_token(token)
    duration_seconds = payload["exp"] - payload["iat"]
    assert duration_seconds == 900  # 15 minutes = 900 seconds


def test_token_additional_custom_claims():
    """9. Additional claims (e.g. role, email) are embedded and decoded properly."""
    subject = "user_with_claims"
    claims = {"role": "merchant_admin", "email": "merchant@example.com"}
    token = create_access_token(subject=subject, additional_claims=claims)

    payload = decode_access_token(token)
    assert payload["sub"] == subject
    assert payload["role"] == "merchant_admin"
    assert payload["email"] == "merchant@example.com"


def test_expired_token_is_rejected():
    """10. Expired tokens are rejected with ExpiredTokenError."""
    subject = "expired_user"
    # Create token that expired 10 seconds ago
    negative_delta = timedelta(seconds=-10)
    expired_token = create_access_token(subject=subject, expires_delta=negative_delta)

    with pytest.raises(ExpiredTokenError) as exc_info:
        decode_access_token(expired_token)

    assert "expired" in str(exc_info.value).lower()


def test_malformed_token_is_rejected():
    """11. Malformed and corrupted tokens are rejected with InvalidTokenError."""
    malformed_tokens = [
        "not.a.valid.jwt.token",
        "invalid_base64_header.payload.signature",
        "header.payload",
        "...",
        "",
        "   ",
    ]
    for bad_token in malformed_tokens:
        with pytest.raises(InvalidTokenError):
            decode_access_token(bad_token)


def test_token_signed_with_wrong_secret_is_rejected():
    """12. Token signed with an untrusted/different secret key is rejected with InvalidTokenError."""
    subject = "forged_token_user"
    # Create token with a different secret
    forged_token = jwt.encode(
        {"sub": subject, "exp": int(time.time()) + 3600, "iat": int(time.time())},
        "attacker_forged_secret_key_1234567890",
        algorithm="HS256",
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(forged_token)


def test_token_with_unsupported_algorithm_rejected():
    """13. Token signed with a different algorithm or none is rejected."""
    subject = "algorithm_confusion_user"
    token = create_access_token(subject=subject)

    # Attempt to decode requiring a different algorithm (e.g. HS512 when signed with HS256)
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, algorithm="HS512")


def test_token_empty_subject_rejected():
    """14. Creating a token with empty subject raises ValueError."""
    with pytest.raises(ValueError):
        create_access_token(subject="")

    with pytest.raises(ValueError):
        create_access_token(subject=None)  # type: ignore


# ==============================================================================
# 3. Configuration & Schema Tests
# ==============================================================================

def test_jwt_settings_configuration():
    """15. Settings object exposes JWT configuration properties with valid defaults."""
    assert hasattr(settings, "JWT_SECRET_KEY")
    assert hasattr(settings, "JWT_ALGORITHM")
    assert hasattr(settings, "JWT_ACCESS_TOKEN_EXPIRE_MINUTES")

    assert isinstance(settings.JWT_SECRET_KEY, str)
    assert len(settings.JWT_SECRET_KEY) >= 16
    assert settings.JWT_ALGORITHM == "HS256"
    assert isinstance(settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES, int)
    assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 0


def test_auth_pydantic_schemas():
    """16. Token and TokenPayload Pydantic schemas validate correctly."""
    token_obj = Token(
        access_token="sample_jwt_access_token_string",
        token_type="bearer",
        expires_in=3600,
    )
    assert token_obj.access_token == "sample_jwt_access_token_string"
    assert token_obj.token_type == "bearer"
    assert token_obj.expires_in == 3600

    payload_obj = TokenPayload(
        sub="user_id_12345",
        exp=1800000000,
        iat=1799996400,
    )
    assert payload_obj.sub == "user_id_12345"
    assert payload_obj.exp == 1800000000
    assert payload_obj.iat == 1799996400
    assert payload_obj.nbf is None
