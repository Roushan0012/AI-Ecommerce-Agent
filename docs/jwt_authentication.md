# Authentication Documentation (Phase 17A, 17B, & 17C)

## 1. Overview
The platform authentication architecture utilizes **Argon2id** password hashing and **RFC 7519 JSON Web Tokens (JWT)** for user identity management, authentication, and endpoint authorization.

```
Registration:
Plaintext Password → Argon2id PasswordHasher → Salted Hash ($argon2id$...) → User Table

Login:
User Credentials → Argon2id Verification → PyJWT (HS256) → Signed JWT Access Token (sub: user.id)

Protected API Access:
HTTP Request with 'Authorization: Bearer <token>' → get_current_user Dependency → Authoritative User Context & Ownership Enforcement
```

> [!NOTE]
> Phase 17A implemented the cryptographic foundation, Phase 17B implemented user registration/login, and Phase 17C protects user commerce endpoints with JWT and cross-user ownership controls. Role-Based Access Control (RBAC) and permissions are deferred to Phase 17D.

---

## 2. Environment Configuration
The authentication subsystem is configured via environment variables in `.env`:

| Variable | Type | Default | Description |
|---|---|---|---|
| `JWT_SECRET_KEY` | `string` | *(dev fallback)* | Cryptographic secret key used to sign and verify HMAC-SHA256 tokens (min 32 chars in production). |
| `JWT_ALGORITHM` | `string` | `HS256` | Cryptographic signature algorithm (default: `HS256`). |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `integer` | `60` | Token validity lifetime in minutes (default: 60 min). |

---

## 3. JWT Authentication Dependency (`get_current_user`)
A reusable FastAPI dependency `get_current_user` (`backend/app/core/dependencies.py`):
1. **Header Validation**: Enforces `Authorization: Bearer <token>`.
2. **Cryptographic Verification**: Verifies HMAC-SHA256 signature, expiration (`exp`), and issued-at (`iat`).
3. **Subject Validation**: Validates UUID format in `sub` claim.
4. **Database Identity Lookup**: Resolves active `User` from PostgreSQL / SQLite.
5. **Rejection Cases (`401 Unauthorized`)**:
   - Missing `Authorization` header
   - Malformed scheme (non-Bearer)
   - Invalid token signature
   - Expired token
   - Nonexistent user in database
   - Inactive user account (`is_active = False`)

---

## 4. API Surface: Public vs Protected vs Agent Boundary

### 4.1 Public Endpoints (No Auth Required)
| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/health` | API health check |
| `GET` | `/api/health/database` | Database connectivity health check |
| `POST` | `/api/auth/register` | User registration |
| `POST` | `/api/auth/login` | User authentication & JWT issuance |
| `GET` | `/api/products` | Catalog listing with filters & pagination |
| `GET` | `/api/products/{id}` | Product detail lookup |
| `POST` | `/api/agent/understand` | AI intent extraction from message |
| `POST` | `/api/agent/search` | AI-assisted product search |
| `POST` | `/api/agent/recommend` | Multi-factor recommendation scoring |
| `POST` | `/api/agent/growth` | Growth engine upsell & cross-sell |
| `POST` | `/api/payments/webhook` | Razorpay webhook (HMAC signature verified) |

### 4.2 JWT Protected User Endpoints (`Authorization: Bearer <token>`)
| Method | Route | Ownership & Access Control |
|---|---|---|
| `POST` | `/api/cart` | Creates or retrieves cart for authenticated user. Client-supplied ID cannot override JWT identity. |
| `GET` | `/api/cart/{customer_id}` | Authenticated user can only view their own cart (`403 Forbidden` on mismatch). |
| `POST` | `/api/cart/{customer_id}/items` | Authenticated user can only modify their own cart (`403 Forbidden` on mismatch). |
| `PUT` | `/api/cart/{customer_id}/items/{product_id}` | Authenticated user can only modify their own cart (`403 Forbidden` on mismatch). |
| `DELETE` | `/api/cart/{customer_id}/items/{product_id}` | Authenticated user can only modify their own cart (`403 Forbidden` on mismatch). |
| `POST` | `/api/orders` | Converts authenticated user's active cart into an order (`403 Forbidden` on mismatch). |
| `GET` | `/api/orders/{customer_id}` | Authenticated user can only view their own orders (`403 Forbidden` on mismatch). |
| `GET` | `/api/orders/{customer_id}/{order_id}` | Authenticated user can only view their own order detail (`403 Forbidden` on mismatch). |
| `POST` | `/api/payments/create-order` | Authenticated user can only create payments for their own orders (`403 Forbidden` on mismatch). |
| `GET` | `/api/audit/{customer_id}` | Authenticated user can only access their own audit trail (`403 Forbidden` on mismatch). |

### 4.3 Machine-to-Machine Agent Endpoints (`X-Agent-Key`)
| Method | Route | Authentication Mechanism |
|---|---|---|
| `POST` | `/api/agent-commerce/discover` | Dedicated `X-Agent-Key` with constant-time HMAC check |
| `GET` | `/api/agent-commerce/products/{id}` | Dedicated `X-Agent-Key` with constant-time HMAC check |
| `POST` | `/api/agent-commerce/inventory/check` | Dedicated `X-Agent-Key` with constant-time HMAC check |
| `POST` | `/api/agent-commerce/cart/items` | Dedicated `X-Agent-Key` with constant-time HMAC check |
| `POST` | `/api/agent-commerce/orders` | Dedicated `X-Agent-Key` with constant-time HMAC check |

> [!IMPORTANT]
> Agent-to-Agent machine commerce is strictly decoupled from user JWT authentication. `X-Agent-Key` does NOT accept JWT tokens, and user endpoints do NOT accept `X-Agent-Key`.

---

## 5. Security & Ownership Rules
1. **Header-Only Authorization**: Access tokens are accepted exclusively via the `Authorization: Bearer <token>` header (never via URL query params or JSON request bodies).
2. **Stateless Tokens**: JWTs are cryptographically signed and verified without storing access tokens in the database.
3. **Strict Ownership Enforcement**:
   - `User A` accessing `User A` resource → `200 OK` / `201 Created`
   - `User A` accessing `User B` resource → `403 Forbidden` ("Access denied")
   - Unauthenticated request → `401 Unauthorized` ("Missing Authorization header")
   - Forged/expired/invalid token → `401 Unauthorized` ("Invalid access token" / "Token has expired")
4. **Authoritative Identity**: The authenticated user's UUID from the verified JWT `sub` claim is authoritative; client-supplied IDs in request payloads cannot override identity.
5. **Phase 12 Guardrails**: Server-authoritative catalog pricing, inventory revalidation, and IDOR protections remain 100% active.
