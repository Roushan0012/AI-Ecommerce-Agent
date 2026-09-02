# Authentication Documentation (Phase 17A & Phase 17B)

## 1. Overview
The platform authentication architecture utilizes **Argon2id** password hashing and **RFC 7519 JSON Web Tokens (JWT)** for user identity management and authentication.

```
Registration:
Plaintext Password → Argon2id PasswordHasher → Salted Hash ($argon2id$...) → User Table

Login:
User Credentials → Argon2id Verification → PyJWT (HS256) → Signed JWT Access Token (sub: user.id)
```

> [!NOTE]
> Phase 17A implemented the cryptographic foundation and Phase 17B implements user registration and login endpoints. Route protection, JWT dependency injection for existing business APIs, and role-based access control are intentionally deferred to Phase 17C.

---

## 2. Environment Configuration
The authentication subsystem is configured via environment variables in `.env`:

| Variable | Type | Default | Description |
|---|---|---|---|
| `JWT_SECRET_KEY` | `string` | *(dev fallback)* | Cryptographic secret key used to sign and verify HMAC-SHA256 tokens (min 32 chars in production). |
| `JWT_ALGORITHM` | `string` | `HS256` | Cryptographic signature algorithm (default: `HS256`). |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `integer` | `60` | Token validity lifetime in minutes (default: 60 min). |

---

## 3. Database Model (`users` table)
- **Table**: `users`
- **Fields**:
  - `id`: `UUID` (Primary Key, unique customer/user identifier).
  - `email`: `VARCHAR(255)` (Normalized lowercase, unique index).
  - `password_hash`: `VARCHAR(255)` (Argon2id hash string).
  - `is_active`: `BOOLEAN` (Default: `TRUE`).
  - `created_at`: `TIMESTAMPTZ` (UTC creation timestamp).
  - `updated_at`: `TIMESTAMPTZ` (UTC update timestamp).

---

## 4. API Endpoints (Phase 17B)

### 4.1 User Registration (`POST /api/auth/register`)
Creates a new customer/user account.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "StrongPassword123!"
  }
  ```
- **Validation Rules**:
  - Email format validated via regex and normalized to lowercase.
  - Password minimum length of 8 characters.
  - Rejects duplicate email with `409 Conflict`.
- **Response (`201 Created`)**:
  ```json
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "email": "user@example.com",
    "is_active": true,
    "created_at": "2026-09-02T18:00:00Z",
    "updated_at": "2026-09-02T18:00:00Z"
  }
  ```
- **Security**: Never returns password or password hash.

### 4.2 User Login (`POST /api/auth/login`)
Authenticates credentials and returns a signed JWT access token.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "StrongPassword123!"
  }
  ```
- **Behavior**:
  - Normalizes email before lookup.
  - Verifies hash using Argon2id in constant time.
  - Rejects unknown email or incorrect password with generic `401 Unauthorized` ("Invalid email or password.") without disclosing user existence.
  - Rejects inactive users with `401 Unauthorized`.
  - Embeds the user UUID as the JWT subject (`sub`).
- **Response (`200 OK`)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600
  }
  ```
- **Security**: JWTs are never stored in the database; tokens are stateless and validated cryptographically.

---

## 5. Security & Isolation Guarantee
1. **Zero Secret Leakage**: `JWT_SECRET_KEY`, raw passwords, and password hashes are never exposed in API responses, logs, or error payloads.
2. **Phase 15 `X-Agent-Key` Independence**: Machine-to-machine Agent-to-Agent commerce continues to use the dedicated `X-Agent-Key` header with constant-time HMAC verification. User JWT authentication is completely decoupled.
3. **Phase 12 Guardrails**: Authoritative backend checks on pricing, inventory, IDOR, and Razorpay webhooks remain fully active.
4. **Scope Boundary**: Existing commerce APIs (Cart, Orders, Products, Payments) remain open to customer session IDs for now; route-level JWT protection is deferred to Phase 17C.
