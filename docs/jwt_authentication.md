# Phase 17A — JWT Authentication Foundation

## 1. Overview
Phase 17A establishes the core cryptographic and authentication foundation for JSON Web Token (JWT) handling and password hashing across the platform.

```
Plaintext Password → Argon2id PasswordHasher → Salted Hash ($argon2id$...)
User Subject + UTC Claims → PyJWT (HS256) → Signed JWT Access Token
```

> [!NOTE]
> In Phase 17A, only the underlying security utilities, configuration, and schemas are implemented. User registration, login endpoints, database models, role-based authorization, and endpoint protection are deferred to Phase 17B.

---

## 2. Environment Configuration
The JWT authentication subsystem is configured via the following environment variables in `.env`:

| Variable | Type | Default | Description |
|---|---|---|---|
| `JWT_SECRET_KEY` | `string` | *(dev placeholder)* | Cryptographic secret key used to sign and verify HMAC-SHA256 tokens (min 32 chars in production). |
| `JWT_ALGORITHM` | `string` | `HS256` | Cryptographic signature algorithm (default: `HS256`). |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `integer` | `60` | Token validity lifetime in minutes (default: 60 min). |

---

## 3. Password Hashing (Argon2id)
- **Algorithm**: **Argon2id** (via `argon2-cffi`), the winner of the Password Hashing Competition (PHC).
- **Properties**: Memory-hard and compute-hard, providing state-of-the-art resistance against GPU/ASIC brute-force and side-channel attacks.
- **Helpers**:
  - `hash_password(password: str) -> str`: Produces a salted Argon2id hash. Never stores or logs plaintext passwords.
  - `verify_password(plain_password: str, hashed_password: str) -> bool`: Verifies candidate password against hash in constant time. Returns `False` safely on corrupted hashes or mismatches.

---

## 4. JWT Access Token Creation & Verification
- **Token Format**: Standard RFC 7519 JSON Web Token (`Header.Payload.Signature`).
- **Timestamps**: All timestamps use timezone-aware UTC (`datetime.now(timezone.utc)`).
- **Core Claims**:
  - `sub`: Subject identifier (user UUID or email string).
  - `iat`: Issued-at UTC epoch timestamp.
  - `exp`: Expiration UTC epoch timestamp.
  - `nbf`: Not-before UTC epoch timestamp.
- **Helpers**:
  - `create_access_token(subject, expires_delta=None, additional_claims=None) -> str`
  - `decode_access_token(token, secret_key=None, algorithm=None) -> Dict[str, Any]`
- **Exceptions**:
  - `ExpiredTokenError`: Raised when current UTC time exceeds `exp`.
  - `InvalidTokenError`: Raised on forged signatures, malformed tokens, algorithm confusion, or missing claims.

---

## 5. Non-Interference with Phase 15 Agent-to-Agent Commerce
- Machine-to-machine Agent-to-Agent commerce continues to use the dedicated `X-Agent-Key` header with constant-time HMAC verification.
- Phase 17A JWT authentication does not alter or replace existing `X-Agent-Key` behavior or Phase 12 security guardrails.
