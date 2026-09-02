# Authentication & Authorization Documentation (Phase 17A, 17B, 17C, & 17D)

## 1. Overview
The platform authentication and authorization architecture combines **Argon2id** password hashing, **RFC 7519 JSON Web Tokens (JWT)** for user identity management, and **Role-Based Access Control (RBAC)** for endpoint authorization and tenant isolation.

```
Registration:
Plaintext Password → Argon2id PasswordHasher → Salted Hash ($argon2id$...) → User Table (role: customer)

Login:
User Credentials → Argon2id Verification → PyJWT (HS256) → Signed JWT Access Token (sub: user.id, role: user.role)

Protected Endpoint Access:
HTTP Request with 'Authorization: Bearer <token>'
   │
   ▼
[get_current_user] ──── Invalid/Missing Token? ───► 401 Unauthorized
   │
   ▼ Verified User Identity (Authoritative DB lookup)
   │
[require_roles] ────── Insufficient Role? ────────► 403 Forbidden
   │
   ▼ Authorized User Context (customer, merchant, or admin)
[Endpoint Execution + Resource Ownership Verification]
```

> [!NOTE]
> Phase 17A implemented the cryptographic foundation, Phase 17B implemented user registration/login, Phase 17C protects user commerce endpoints with JWT and ownership controls, and Phase 17D implements role-based authorization (`customer`, `merchant`, `admin`), privilege-escalation prevention, and dashboard/admin role boundaries.

---

## 2. Controlled Role Set

The platform enforces a minimal, controlled role set:

| Role | Permitted Actions | Accessible Endpoints | Default Assignment |
|---|---|---|---|
| `customer` | Browse catalog, use AI shopping assistant, manage personal cart, place orders, make payments, inspect personal audit trail. | `/api/cart/*`, `/api/orders/*`, `/api/payments/create-order`, `/api/audit/{customer_id}` | **Default for all new registrations** |
| `merchant` | Customer capabilities + merchant dashboard analytics, revenue metrics, order lists, and agent activity feed. | All customer endpoints + `/api/dashboard/overview`, `/api/dashboard/orders`, `/api/dashboard/activity` | Assigned administratively / seeded |
| `admin` | Full platform oversight: inspect system status, platform-wide audit events, cross-customer audit trails, and merchant dashboards. | All endpoints + `/api/admin/system/status`, `/api/admin/audit-logs`, `/api/audit/admin/all` | Assigned administratively / seeded |

### 2.1 Privilege Escalation Prevention
- **Registration Role Sanitization**: Public registration (`/api/auth/register`) strictly sets `role="customer"`. Any client attempt to submit `{"role": "admin"}` or `{"role": "merchant"}` is completely discarded; the user is created with the `customer` role.
- **Server-Authoritative Role Verification**: Authorization checks inspect the authoritative database record (`current_user.role`). Client-supplied request body roles or forged token claims are disregarded.
- **No Self-Modification API**: No public API exists that allows users to alter their own role or another user's role.
- **Model Validation**: The SQLAlchemy `User` model employs `@validates("role")` to reject any arbitrary or unapproved role strings at the ORM layer.

---

## 3. Environment Configuration
The authentication subsystem is configured via environment variables in `.env`:

| Variable | Type | Default | Description |
|---|---|---|---|
| `JWT_SECRET_KEY` | `string` | *(dev fallback)* | Cryptographic secret key used to sign and verify HMAC-SHA256 tokens (min 32 chars in production). |
| `JWT_ALGORITHM` | `string` | `HS256` | Cryptographic signature algorithm (default: `HS256`). |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `integer` | `60` | Token validity lifetime in minutes (default: 60 min). |

---

## 4. Authorization Dependencies

FastAPI authorization dependencies (`backend/app/core/dependencies.py`) build directly on top of `get_current_user`:

```python
require_customer = require_roles(UserRole.CUSTOMER.value, UserRole.MERCHANT.value, UserRole.ADMIN.value)
require_merchant = require_roles(UserRole.MERCHANT.value, UserRole.ADMIN.value)
require_admin = require_roles(UserRole.ADMIN.value)
```

### 4.1 Distinction Between 401 and 403
- **`401 Unauthorized`**: Authentication failure. The request lacks valid authentication credentials.
  - Missing `Authorization` header
  - Malformed scheme (non-Bearer)
  - Cryptographically invalid signature
  - Expired token
  - User not found in database or account inactive
- **`403 Forbidden`**: Authorization failure. The request is authenticated, but the user does not have permission.
  - Customer accessing merchant dashboard (`/api/dashboard/*`)
  - Customer or merchant accessing admin endpoints (`/api/admin/*`, `/api/audit/admin/all`)
  - Customer attempting to access or modify another customer's cart, orders, or audit trail (cross-user violation)

---

## 5. API Surface & Protection Matrix

### 5.1 Public Endpoints (No Authentication Required)
| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/health` | API health check |
| `GET` | `/api/health/database` | Database connectivity health check |
| `POST` | `/api/auth/register` | Customer user registration (always role: customer) |
| `POST` | `/api/auth/login` | User authentication & JWT issuance |
| `GET` | `/api/products` | Public catalog listing with filters & pagination |
| `GET` | `/api/products/{id}` | Public product detail lookup |
| `POST` | `/api/agent/understand` | Public AI intent extraction from natural language |
| `POST` | `/api/agent/search` | Public AI-assisted product search |
| `POST` | `/api/agent/recommend` | Public multi-factor recommendation scoring |
| `POST` | `/api/agent/growth` | Public growth engine upsell & cross-sell |
| `POST` | `/api/payments/webhook` | Razorpay webhook (HMAC signature verified) |

### 5.2 Customer Protected Endpoints (`require_customer`)
| Method | Route | Role & Ownership Enforcement |
|---|---|---|
| `POST` | `/api/cart` | Creates or retrieves cart for authenticated user. Client ID cannot override JWT identity. |
| `GET` | `/api/cart/{customer_id}` | Authenticated user can only view their own cart (`403 Forbidden` on mismatch). |
| `POST` | `/api/cart/{customer_id}/items` | Authenticated user can only modify their own cart (`403 Forbidden` on mismatch). |
| `PUT` | `/api/cart/{customer_id}/items/{product_id}` | Authenticated user can only modify their own cart (`403 Forbidden` on mismatch). |
| `DELETE` | `/api/cart/{customer_id}/items/{product_id}` | Authenticated user can only modify their own cart (`403 Forbidden` on mismatch). |
| `POST` | `/api/orders` | Converts authenticated user's active cart into an order (`403 Forbidden` on mismatch). |
| `GET` | `/api/orders/{customer_id}` | Authenticated user can only view their own orders (`403 Forbidden` on mismatch). |
| `GET` | `/api/orders/{customer_id}/{order_id}` | Authenticated user can only view their own order detail (`403 Forbidden` on mismatch). |
| `POST` | `/api/payments/create-order` | Authenticated user can only initiate payments for their own orders (`403 Forbidden` on mismatch). |
| `GET` | `/api/audit/{customer_id}` | Authenticated user can access their own audit trail; admin has oversight (`403 Forbidden` otherwise). |

### 5.3 Merchant Protected Endpoints (`require_merchant`)
| Method | Route | Role Requirement |
|---|---|---|
| `GET` | `/api/dashboard/overview` | Merchant or Admin (`role: merchant` or `admin`). Customer receives `403 Forbidden`. |
| `GET` | `/api/dashboard/orders` | Merchant or Admin (`role: merchant` or `admin`). Customer receives `403 Forbidden`. |
| `GET` | `/api/dashboard/activity` | Merchant or Admin (`role: merchant` or `admin`). Customer receives `403 Forbidden`. |

### 5.4 Admin Protected Endpoints (`require_admin`)
| Method | Route | Role Requirement |
|---|---|---|
| `GET` | `/api/admin/system/status` | Strictly Admin (`role: admin`). Customer and merchant receive `403 Forbidden`. |
| `GET` | `/api/admin/audit-logs` | Strictly Admin (`role: admin`). Customer and merchant receive `403 Forbidden`. |
| `GET` | `/api/audit/admin/all` | Strictly Admin (`role: admin`). Customer and merchant receive `403 Forbidden`. |

### 5.5 Machine-to-Machine Agent Endpoints (`X-Agent-Key`)
| Method | Route | Authentication Mechanism |
|---|---|---|
| `POST` | `/api/agent-commerce/discover` | Dedicated `X-Agent-Key` with constant-time HMAC verification |
| `GET` | `/api/agent-commerce/products/{id}` | Dedicated `X-Agent-Key` with constant-time HMAC verification |
| `POST` | `/api/agent-commerce/inventory/check` | Dedicated `X-Agent-Key` with constant-time HMAC verification |
| `POST` | `/api/agent-commerce/cart/items` | Dedicated `X-Agent-Key` with constant-time HMAC verification |
| `POST` | `/api/agent-commerce/orders` | Dedicated `X-Agent-Key` with constant-time HMAC verification |
| `POST` | `/api/agent-commerce/payments/initiate` | Dedicated `X-Agent-Key` with constant-time HMAC verification |

> [!IMPORTANT]
> Agent-to-Agent machine commerce is strictly decoupled from user JWT authentication. `X-Agent-Key` does NOT accept user JWT tokens, and user endpoints do NOT accept `X-Agent-Key`.

---

## 6. Authentication Boundaries & Isolation (Phase 17E)

The platform enforces strict cryptographic and architectural isolation between three independent authentication mechanisms:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           AUTHENTICATION BOUNDARIES                              │
├─────────────────────────┬───────────────────────────────┬────────────────────────┤
│ Mechanism               │ Header                        │ Target Endpoints       │
├─────────────────────────┼───────────────────────────────┼────────────────────────┤
│ Human User Auth         │ Authorization: Bearer <JWT>   │ /api/cart/*            │
│                         │                               │ /api/orders/*          │
│                         │                               │ /api/dashboard/*       │
│                         │                               │ /api/admin/*           │
├─────────────────────────┼───────────────────────────────┼────────────────────────┤
│ Machine Agent Commerce  │ X-Agent-Key: <key>            │ /api/agent-commerce/*  │
├─────────────────────────┼───────────────────────────────┼────────────────────────┤
│ Razorpay Webhook        │ X-Razorpay-Signature: <HMAC>  │ /api/payments/webhook  │
└─────────────────────────┴───────────────────────────────┴────────────────────────┘
```

1. **User JWT (`Authorization: Bearer <JWT>`)**:
   - Designed for human users (customers, merchants, and platform administrators).
   - Validates user identity and role against the authoritative PostgreSQL database.
   - **Agent Boundary**: A user JWT (even an admin JWT) is rejected with `401 Unauthorized` on `/api/agent-commerce/*`.

2. **Machine-to-Machine Agent Key (`X-Agent-Key`)**:
   - Designed for external automated buyer agents interacting directly with catalog discovery and automated ordering.
   - Validated in constant time using `hmac.compare_digest`.
   - **User Boundary**: An `X-Agent-Key` cannot substitute for a JWT; sending it to `/api/cart`, `/api/orders`, `/api/dashboard/*`, or `/api/admin/*` results in `401 Unauthorized` ("Missing Authorization header").

3. **External Payment Webhook (`X-Razorpay-Signature: HMAC-SHA256`)**:
   - Dedicated webhook endpoint `/api/payments/webhook` exclusively verifies cryptographic HMAC-SHA256 signatures generated with `RAZORPAY_WEBHOOK_SECRET`.
   - Neither a User JWT nor an `X-Agent-Key` can authenticate or bypass webhook verification; requests without a valid HMAC signature return `400 Bad Request`.

---

## 7. Security & Guardrail Guarantees
1. **Header-Only Authorization**: User access tokens are accepted exclusively via `Authorization: Bearer <token>`.
2. **Authoritative Database Context**: Roles and identities are always re-validated against the database; claims inside the token payload are treated as advisory metadata.
3. **Defense Against Privilege Escalation**:
   - Client-supplied `role` during registration is discarded.
   - Client-supplied `customer_id` or `role` in request bodies cannot override JWT context.
   - Role modification requests are rejected.
4. **Strict Mechanism Isolation**: Credentials from one boundary cannot be used to authenticate requests in another boundary.
5. **Phase 12 Guardrails Intact**: Server-authoritative catalog pricing, inventory revalidation, and IDOR protections remain 100% active.
6. **Zero Secrets in Responses/Logs**: Passwords, password hashes, JWT secrets, agent keys, and webhook secrets are never logged or returned in responses.

---

## 8. Phase 17 Final Security & Hardening Summary (Phase 17F)

| Security Domain | Hardening & Protection Mechanism | Verification Status |
|---|---|---|
| **JWT Authentication** | Stateless HS256 tokens (`sub`, `role`, `exp`, `iat`) signed via environment configuration; strictly requires `Authorization: Bearer <token>`; rejects missing, malformed, non-Bearer, expired, forged, non-UUID subject, nonexistent user, and inactive account tokens with sanitized `401 Unauthorized` responses without stack traces. | **VERIFIED** (10+ focused tests) |
| **Registration & Login** | High-entropy Argon2id password hashing; rejection of weak passwords; generic `401 Invalid email or password` for both incorrect passwords and nonexistent accounts to prevent user enumeration; registration forces `customer` role and discards client privilege escalation attempts. | **VERIFIED** (16+ focused tests) |
| **Protected Commerce APIs** | Real-time database revalidation (`get_current_user`); cross-customer IDOR protection on cart and orders; server-authoritative customer identity derived exclusively from the token. | **VERIFIED** (17+ focused tests) |
| **Role Authorization** | Granular RBAC (`customer`, `merchant`, `admin`) via `require_customer`, `require_merchant`, and `require_admin`; customers blocked from merchant dashboard (`403`); customers and merchants blocked from platform admin APIs (`403`); database is authoritative. | **VERIFIED** (20+ focused tests) |
| **A2A Boundary Isolation** | Autonomous agent endpoints (`/api/agent-commerce/*`) exclusively require `X-Agent-Key` verified in constant time (`hmac.compare_digest`); User JWTs (even Admin JWTs) cannot authenticate to agent routes (`401`); `X-Agent-Key` cannot substitute for User JWT on user endpoints (`401`). | **VERIFIED** (13+ focused tests) |
| **Payment & Webhook Security** | Payment order creation enforces order ownership (IDOR defense); clients cannot mark orders paid directly; external Razorpay webhook exclusively validates HMAC-SHA256 signatures via `X-Razorpay-Signature`; duplicate events handled idempotently. | **VERIFIED** (10+ webhook tests) |
| **Comprehensive Test Suite** | 309 pytest tests passing (100%), 54 Newman requests passing (108 assertions), Next.js production build clean, zero tracked secrets or `.env` files. | **VERIFIED** |
