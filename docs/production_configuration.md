# Production Configuration Foundation (Phase 18A)

This document describes the environment configuration architecture, production validation safeguards, CORS policies, and development vs. production behavior for the AI Commerce Agent platform.

---

## 1. Environment Modes (`ENVIRONMENT`)

The platform's runtime behavior is strictly partitioned across three standardized environment modes:

| Mode | Trigger / Value | Description |
|---|---|---|
| `development` | `ENVIRONMENT=development` (Default) | Permissive local development mode with safe fallback placeholders, enabled debug logs, and interactive OpenAPI documentation. |
| `test` | `ENVIRONMENT=test` (or pytest execution) | Automated test mode ensuring seamless in-memory database execution, deterministic AI providers, and credential mocks. |
| `production` | `ENVIRONMENT=production` | Hardened production mode. Requires explicit production-grade secrets, disables debug and stack traces, enforces strict CORS domain validation, and disables public OpenAPI documentation. |

---

## 2. Production Security & Startup Validation

When `ENVIRONMENT=production` is detected, `validate_production_config()` runs automatically during the FastAPI application lifespan startup.

If any required variable is missing or retains an insecure development/test placeholder, startup terminates immediately with a `ConfigurationError`.

> [!IMPORTANT]
> **Zero Secret Leakage in Errors**: Configuration validation error messages strictly report parameter names (e.g. `JWT_SECRET_KEY`, `DATABASE_URL`). The actual secret values or partial strings are never logged or returned in error messages.

### Critical Production Parameters

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        REQUIRED PRODUCTION CONFIGURATION PARAMETERS                    │
├──────────────────────────┬──────────────────────────────┬──────────────────────────────┤
│ Environment Variable     │ Constraint                   │ Insecure Placeholders Blocked│
├──────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│ DATABASE_URL             │ Valid PostgreSQL connection  │ Empty or "sqlite://*"        │
│ JWT_SECRET_KEY           │ Minimum 32 characters        │ Insecure dev placeholder     │
│ COMMERCE_AGENT_KEY       │ Minimum 16 characters        │ "ag_live_key_test_commerce*" │
│ RAZORPAY_KEY_ID          │ Valid production Key ID      │ "rzp_test_placeholder"       │
│ RAZORPAY_KEY_SECRET      │ Non-empty secret             │ Empty                        │
│ RAZORPAY_WEBHOOK_SECRET  │ Non-empty webhook secret     │ "test_webhook_secret_key_123"│
│ CORS_ORIGINS             │ Explicit domains (no '*')    │ Wildcard '*'                 │
└──────────────────────────┴──────────────────────────────┴──────────────────────────────┘
```

---

## 3. Debug & Exception Separation

In production (`ENVIRONMENT=production`):
1. **Debug Flag Overridden**: `settings.DEBUG` evaluates strictly to `False`, ignoring any `DEBUG=true` environment setting.
2. **Interactive Docs Disabled**: `/docs`, `/redoc`, and `/openapi.json` are disabled by default (can be selectively re-enabled if `ENABLE_DOCS=true`).
3. **Internal Error Masking**: Any unhandled server exception (`500 Internal Server Error`) returns a sanitized generic JSON response:
   ```json
   {
       "detail": "An internal server error occurred. Please contact support."
   }
   ```
   Internal stack traces, database schemas, and connection strings are suppressed from API clients.

---

## 4. CORS Configuration (`CORS_ORIGINS`)

Cross-Origin Resource Sharing is controlled via the `CORS_ORIGINS` environment variable.

### Format Support
- **Comma-Separated List**:
  ```bash
  CORS_ORIGINS=https://store.example.com,https://merchant.example.com
  ```
- **JSON Array String**:
  ```bash
  CORS_ORIGINS='["https://store.example.com", "https://merchant.example.com"]'
  ```

### Security Enforcements
- **Development/Test Defaults**: `["http://localhost:3000", "http://127.0.0.1:3000"]`
- **Production Guardrail**: Because `allow_credentials=True` is enabled for authenticated JWT operations, wildcard origins (`"*"`) are **strictly prohibited** in production. Attempting to start the application with `CORS_ORIGINS=*` in production raises a `ConfigurationError`.

---

## 5. Development vs. Production Comparison

| Feature | Development Mode | Production Mode |
|---|---|---|
| **Environment Flag** | `ENVIRONMENT=development` | `ENVIRONMENT=production` |
| **Debug Mode** | Configurable (Default: `true`) | Strictly `false` |
| **OpenAPI / Swagger** | Enabled at `/docs` and `/redoc` | Disabled by default |
| **CORS Origins** | `localhost:3000`, `127.0.0.1:3000` | Explicit production domain(s) |
| **Wildcard CORS (`*`)** | Allowed (non-production only) | Forbidden (`ConfigurationError`) |
| **Fallback Secrets** | Permitted for local development | Forbidden (`ConfigurationError`) |
| **500 Error Responses** | Contains exception detail | Masked generic error response |

---

## 6. Continuous Integration (CI/CD) Quality & Failure Safety (Phase 18B-2)

The automated GitHub Actions CI pipeline ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)) validates every push and pull request targeting `main`.

### Validation Scope
1. **Backend Test Suite (`backend-tests`)**:
   - Sets up Python 3.12 runner with pip caching keyed on `backend/requirements.txt`.
   - Installs pinned dependencies from `backend/requirements.txt`.
   - Executes the full backend test suite (`pytest -v`) under `ENVIRONMENT=test`, SQLite isolated database, and mock AI provider.
   - Validates models, business rules, payment flows, A2A machine endpoints, RBAC, and security regression guardrails.
2. **Frontend Production Build (`frontend-build`)**:
   - Sets up Node.js 20 runner with npm caching keyed on `frontend/package-lock.json`.
   - Installs dependencies reproducibly using `npm ci`.
   - Executes `npm run build` to verify TypeScript compile integrity, Turbopack packaging, and Next.js static page generation.

### Failure Propagation & Fail-Fast Safety
- **No Error Suppression**: No required job or step uses `continue-on-error: true`.
- **Exit Code Integrity**: Pytest and Next.js build run as direct shell commands; multi-line scripts run with explicit bash shell defaults (`-eo pipefail`).
- **Independent Diagnostics**: Backend and frontend jobs run independently in parallel, providing clear visual diagnosis in the GitHub Actions UI.
- **Concurrency Control**: Concurrency groups (`${{ github.workflow }}-${{ github.ref }}`) automatically cancel superseded runs on open pull requests while allowing full commit runs to complete on `main`.

### Dependency Determinism
- Backend uses explicit `pip install -r backend/requirements.txt` with dependency caching.
- Frontend uses clean `npm ci` referencing `frontend/package-lock.json` with dependency caching, preventing lockfile drifts or unintended package updates.

### Security & Environment Isolation
- **Least Privilege Permissions**: CI runs with minimal permissions (`permissions: contents: read`).
- **Zero Secrets Required**: CI requires zero production secrets, API keys, or database URLs in GitHub repository secrets.
- **No Leakage via Logs or Artifacts**: CI never outputs or references `.env` files and creates no external build artifact uploads.
- **Strict File Isolation**: Both root `.gitignore` and `frontend/.gitignore` exclude `.env`, `.env.local`, and sensitive certificate/key patterns.
- **Uncompromised Production Guardrails**: CI runs under test mode without weakening or bypassing `validate_production_config()` checks.

### Developer Troubleshooting
When CI reports a failure:
1. **Backend Test Failures**:
   - Reproduce locally: `backend/.venv/bin/pytest backend/tests/ -v`
   - Inspect specific failing test line and assertion output in CI step logs.
   - Verify that all environment variables use safe test defaults in `Settings`.
2. **Frontend Build Failures**:
   - Reproduce locally: `cd frontend && npm ci && npm run build`
   - Inspect Next.js build logs for TypeScript type errors or syntax mistakes.
   - Ensure all public client-side environment variables have the `NEXT_PUBLIC_` prefix.

---

## 7. API & Application Hardening (Phase 18C)

Phase 18C reinforces the production security posture through multi-layer application defenses:

### 1. In-Memory Rate Limiting
- **Architecture**: Thread-safe sliding-window limiter without external infrastructure dependencies.
- **Tiers & Defaults**:
  - **Auth Tier** (`/api/auth/login`, `/api/auth/register`):
    `RATE_LIMIT_AUTH_PER_MINUTE=10` (Production) / `30` (Development) / `1000` (Test).
  - **Default Tier** (`/api/*`):
    `RATE_LIMIT_DEFAULT_PER_MINUTE=120` (Production) / `300` (Development) / `10000` (Test).
  - **Master Switch**: `RATE_LIMIT_ENABLED=true` (can be toggled via environment).
- **Enforcement**: Excessive requests immediately return `429 Too Many Requests` with a `Retry-After: <seconds>` response header. System health endpoints (`/api/health`, `/api/health/database`) and OpenAPI docs are whitelisted from rate limiting.

### 2. Request Body Size & Input Protections
- **Payload Size Limiting**: `MAX_REQUEST_BODY_BYTES=2097152` (2 MB default, configurable). Requests exceeding this limit receive an immediate `413 Payload Too Large` rejection before extensive memory allocation or streaming occurs.
- **Input Field Boundaries**: Credentials and prompts enforce strict length limits (e.g. login passwords max 128 characters, search prompts max 1000 characters) to prevent CPU exhaustion on hash verification or LLM calls.

### 3. Defensive HTTP Security Headers
All responses automatically receive standard defensive security headers:
- `X-Content-Type-Options: nosniff` (MIME-sniffing protection)
- `X-Frame-Options: DENY` (Clickjacking / frame embedding protection)
- `X-XSS-Protection: 1; mode=block` (Legacy reflected XSS protection)
- `Referrer-Policy: strict-origin-when-cross-origin` (Information disclosure control)
- `Permissions-Policy: camera=(), microphone=(), geolocation=()` (Restricts unauthorized device APIs)
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (Enforced automatically in production mode)

### 4. Error Handling & Information Disclosure Safeguards
- **Validation Error Sanitization**: When a 422 Unprocessable Content error occurs, submitted values for sensitive fields (`password`, `secret`, `token`, `key`) are masked with `[REDACTED]` so passwords and credentials are never reflected back in API responses.
- **Production 500 Error Masking**: Unhandled server exceptions in production return a generic sanitized response without stack traces, database strings, or internal paths.

### 5. Production Logging & Secret Redaction
- **Global Logging Filter**: `SensitiveDataRedactionFilter` automatically sanitizes all log output across root, uvicorn, and application loggers.
- **Patterns Redacted**: Passwords, JWT access tokens, Bearer authorization headers, X-Agent-Key headers, Razorpay keys/signatures, Groq/OpenAI API keys, and PostgreSQL database URLs containing passwords.

---

## 8. Frontend Production Configuration & Authentication (Phase 18D)

Phase 18D establishes production-ready frontend configuration, JWT authentication management, and boundary isolation:

### 1. Centralized API Base URL Configuration
- **Variable**: `NEXT_PUBLIC_API_BASE_URL`
- **Development Default**: `http://127.0.0.1:8000`
- **Production Deployment**: Set to the absolute HTTPS domain of the FastAPI backend (e.g. `https://api.yourdomain.com`).
- **Implementation**: Centralized in [`frontend/src/lib/api.ts`](file:///Users/roushan_iiitbgp/Desktop/AI_Agent_Ecommerce_Platform/frontend/src/lib/api.ts), enabling deployments to connect to external backend clusters without source-code edits.

### 2. Client-Side JWT Authentication Architecture
- **Token Storage**: Only the signed JWT access token string is stored in browser storage (`localStorage`), managed via [`frontend/src/lib/auth.ts`](file:///Users/roushan_iiitbgp/Desktop/AI_Agent_Ecommerce_Platform/frontend/src/lib/auth.ts).
- **Request Authorization**: All protected API requests (`authFetch`, `getAuthHeaders`) automatically inject `Authorization: Bearer <access_token>`.
- **401 Unauthorized Handling**: If an API request receives a 401 response (due to expiration, revocation, or invalidation), client auth state is immediately purged via `clearAuth()`, preventing repeated failed loops.
- **Token Expiry Detection**: Client inspects standard JWT `exp` claims (`decodeJwtPayload`, `isTokenExpired`) for early expiry detection with a 5-second clock skew buffer.
- **Profile Hydration**: `fetchCurrentUser()` queries `GET /api/auth/me` on startup to validate the token authoritatively against the database.

### 3. Role-Based Access Control Alignment
- **Roles**: `customer`, `merchant`, `admin`.
- **Convenience Gate**: Frontend UI guards adapt based on the user's role (e.g. merchant dashboard displays login gate for unauthenticated users or customer accounts).
- **Security Guarantee**: Frontend role checks are treated strictly as UI convenience. The FastAPI backend with `require_merchant`, `require_admin`, and `require_customer` remains the sole authoritative RBAC security boundary.

### 4. Boundary Isolation & Secret Safety
- **Machine A2A Decoupling**: Frontend source code never references, possesses, or transmits `COMMERCE_AGENT_KEY` or the `X-Agent-Key` header. Machine commerce (`/api/agent-commerce/*`) remains strictly server-to-server.
- **Payment Gateway Security**: Server-side Razorpay webhook HMAC signatures and secrets remain untouched. Only the public `NEXT_PUBLIC_RAZORPAY_KEY_ID` is exposed for client checkout modal rendering.
- **Zero Secrets in Public Environment**: `JWT_SECRET_KEY`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, and `DATABASE_URL` are strictly excluded from frontend environment files and `NEXT_PUBLIC_*` namespaces.

---

## 9. Continuous Integration & Pipeline Hardening (Phase 18E)

Phase 18E establishes end-to-end automated validation on every commit and pull request:

### 1. Workflow Architecture & Triggers
- **File**: [`.github/workflows/ci.yml`](file:///Users/roushan_iiitbgp/Desktop/AI_Agent_Ecommerce_Platform/.github/workflows/ci.yml)
- **Triggers**:
  - `push` targeting `main`.
  - `pull_request` targeting `main`.
  - `workflow_dispatch` (on-demand manual trigger).
- **Concurrency Control**: PR runs cancel superseded jobs automatically (`cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}`), conserving CI resources while preserving history on `main`.
- **Least Privilege**: Global `permissions: contents: read` restricts runner tokens to read-only access.
- **Fail-Fast Error Handling**: Strict bash defaults (`-eo pipefail`) without `continue-on-error`.

### 2. Backend Test Job (`backend-tests`)
- **Runtime**: Python 3.12 on Ubuntu Latest.
- **Dependency Handling**: Deterministic `pip install -r backend/requirements.txt` with pip caching.
- **Test Execution**: Full backend pytest suite (`pytest -v`) in isolated test mode (`ENVIRONMENT=test`, SQLite in-memory/file test database, deterministic mock AI provider).
- **Security Check**: Includes repository-wide secret scanning (`test_repository_wide_secret_leak_prevention`) ensuring zero committed credentials.

### 3. Frontend Test & Build Job (`frontend-build`)
- **Runtime**: Node.js 20 on Ubuntu Latest.
- **Dependency Handling**: Locked `npm ci` with npm caching referencing `frontend/package-lock.json`.
- **Test Suite**: Executes `npm test` verifying client-side authentication, auth headers, token expiration, and secret boundary isolation.
- **Production Build**: Executes `npm run build` (`NEXT_TELEMETRY_DISABLED=1`, `CI=true`) ensuring TypeScript type-checking and Next.js static page generation complete cleanly.

### 4. What CI Does NOT Do
- **No Cloud Deployment**: CI only validates code correctness and buildability; it does not deploy to production or manage cloud infrastructure (reserved for future deployment phases).
- **No Production Secrets**: CI never connects to live databases, production Razorpay instances, or external LLM APIs.

---

## 10. Deployment Architecture & Configuration Foundation (Phase 18F-1)

Phase 18F-1 establishes the deployment configuration foundation across the application stack without introducing premature cloud infrastructure or altering application logic:

### 1. Three-Tier Deployment Architecture
```
┌─────────────────────────┐          HTTPS / Bearer JWT          ┌─────────────────────────┐
│     Next.js Frontend    │ ───────────────────────────────────► │     FastAPI Backend     │
│  (React 19 / Next 16)   │                                      │  (Uvicorn ASGI Engine)  │
└─────────────────────────┘                                      └────────────┬────────────┘
             │                                                                │
             │ Client Checkout Modal                                          │ SQLAlchemy ORM
             ▼                                                                ▼
┌─────────────────────────┐                                      ┌─────────────────────────┐
│  Razorpay Payment Form  │                                      │   PostgreSQL / Supabase │
│    (Public Key ID)      │                                      │ (Connection Pool / SSL) │
└─────────────────────────┘                                      └─────────────────────────┘
                                                                              │
                                 ┌──────────────────────────────┬─────────────┴─────────────┐
                                 ▼                              ▼                           ▼
                     ┌───────────────────────┐      ┌───────────────────────┐   ┌───────────────────────┐
                     │ External Agents (A2A) │      │  Razorpay Webhooks    │   │ AI Provider (Groq/OAI)│
                     │ (X-Agent-Key machine) │      │ (HMAC-SHA256 verified)│   │  (Server-side calls)  │
                     └───────────────────────┘      └───────────────────────┘   └───────────────────────┘
```

- **Client Tier (Next.js)**: Static and SSR front-end communicating with the backend over HTTPS using bearer tokens.
- **Application Tier (FastAPI)**: Stateless ASGI application handling business logic, guardrails, rate limiting, and RBAC authorization.
- **Data Tier (PostgreSQL / Supabase)**: Persistent relational store with foreign key constraints, transactional consistency, and connection pooling.
- **External Integration Boundaries**:
  - **Razorpay**: Client triggers checkout using public `NEXT_PUBLIC_RAZORPAY_KEY_ID`. Backend securely creates orders via `RAZORPAY_KEY_SECRET` and verifies payment webhooks via `RAZORPAY_WEBHOOK_SECRET` HMAC-SHA256 signature checking.
  - **External Commerce Agents**: Connect exclusively via machine-to-machine endpoints (`/api/agent-commerce/*`) authenticated by constant-time `X-Agent-Key` validation.
  - **AI Providers**: Server-side communication with Groq or OpenAI APIs using backend-held `AI_API_KEY`. Never exposed to client.

### 2. Environment Matrix Comparison

| Characteristic | Local / Development | CI / Test | Production |
|---|---|---|---|
| `ENVIRONMENT` | `development` | `test` | `production` |
| `DEBUG` | `true` (configurable) | `false` | `false` (strictly enforced) |
| **Server Binding** | `127.0.0.1:8000` | Mock / TestClient | `0.0.0.0:8000` (all interfaces) |
| **Concurrency** | Single process (`--reload` optional) | Single process test worker | Multi-worker (`--workers 4`) |
| **Database** | PostgreSQL or SQLite | SQLite (`sqlite:///./ci_test.db`) | Managed PostgreSQL (Supabase SSL) |
| **CORS Origins** | `localhost:3000`, `127.0.0.1:3000` | Permissive for tests | Strict domain whitelist (no wildcard `*`) |
| **Rate Limiting** | 30 auth / 300 default per min | 1000 auth / 10000 default | 10 auth / 120 default per min |
| **Security Headers** | Basic headers | Basic headers | Strict HSTS, nosniff, DENY, origin |
| **OpenAPI Docs** | Enabled (`/docs`, `/redoc`) | Disabled | Disabled (enabled only via `ENABLE_DOCS=true`) |
| **Error Handling** | Detailed exceptions in dev | Assertions & tracebacks | Masked 500 responses & redacted 422s |

### 3. Backend Production Startup Readiness
- **Production Startup Command**:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-4} --proxy-headers --forwarded-allow-ips "*"
  ```
- **Readiness Properties**:
  - `--host 0.0.0.0`: Required by cloud containers and virtual machines to accept external ingress traffic.
  - `--port ${PORT:-8000}`: Binds dynamically to container orchestrator-allocated ports (e.g. Render, Railway, Fly.io, Cloud Run).
  - `--workers 4`: Provides parallel request execution across CPU cores.
  - `--proxy-headers --forwarded-allow-ips "*"`: Accurately extracts client IPs from reverse proxy `X-Forwarded-For` headers for sliding-window rate limiting.
  - **No Reload**: Development `--reload` is omitted to eliminate file-watching memory overhead.
  - **Zero Code Changes Needed**: The existing entry point `app.main:app` is completely production-ready.

### 4. Frontend Production Configuration
- **API Base URL**: Configured via `NEXT_PUBLIC_API_BASE_URL` (e.g. `https://api.yourdomain.com`).
- **Production Build Command**:
  ```bash
  cd frontend && npm ci && npm run build
  ```
- **Production Start Command**:
  ```bash
  cd frontend && npm run start -- -p ${PORT:-3000}
  ```
- **Security Boundary**: Only `NEXT_PUBLIC_*` variables are bundled into client assets. All database URLs, JWT signing secrets, Razorpay secrets, and machine keys remain completely isolated on the server.

### 5. Localhost & Development Assumption Audit
- **Findings**:
  - `CORS_ORIGINS`: Safe development default (`http://localhost:3000`, `http://127.0.0.1:3000`), strictly requires explicit domain configuration in production (`validate_production_config`).
  - `NEXT_PUBLIC_API_BASE_URL`: Safe development fallback (`http://127.0.0.1:8000`), dynamically overridden in production via environment variable.
  - `HOST` and `PORT`: Local default `127.0.0.1:8000`, production default `0.0.0.0:8000`.
- **Verdict**: Zero hardcoded production blockers exist. All local defaults function correctly in development while enabling complete environment configuration in production.

### 6. Phase 18F Roadmap Progression
- **Backend Containerization & Readiness (Phase 18F-2)**: Implemented below.
- **Frontend & Full-Stack Deployment Preparation (Phase 18F-3)**: Multi-container orchestration, frontend containerization, deployment scripts.
- **Actual Cloud Infrastructure Provisioning**: Deferred to deployment execution step.

---

## 11. Backend Deployment Readiness (Phase 18F-2)

Phase 18F-2 hardens the FastAPI backend runtime for containerized and virtualized deployments while preserving all core business logic and API contracts:

### 1. Production Startup Readiness
- **ASGI Process Engine**: Uvicorn with standard asyncio loop (`uvloop`), HTTP/1.1 parsing (`httptools`), and proxy headers (`--proxy-headers --forwarded-allow-ips "*"`).
- **Process Entry Point**: `app.main:app` (zero modifications required to application structure).
- **Multi-Worker Concurrency**: Driven by `${WEB_CONCURRENCY:-4}` to achieve multi-core throughput in production containers/VMs.
- **Dynamic Port & Host Binding**: Driven by `${HOST:-0.0.0.0}` and `${PORT:-8000}`.
- **Disabling Development Reload**: `--reload` is strictly omitted from production commands, preventing filesystem watcher overhead and process instability.

### 2. Database Readiness & Prevention of SQLite Fallback
- **Strict PostgreSQL / Supabase Requirement**: In production (`ENVIRONMENT=production`), the application strictly connects to PostgreSQL/Supabase via `DATABASE_URL`.
- **No Accidental SQLite Fallback**: While local development may fall back to `commerce.db` when working offline, `database.get_engine()` strictly blocks SQLite fallback in production. If the primary database connection fails, the PostgreSQL engine is preserved and an error is logged.
- **Sanitized Logging**: Database error messages and connection strings are scrubbed with `redact_sensitive_text()` before logging, preventing credential leaks in application log streams.
- **Connection Pooling & Pre-Ping**: Database engines use `pool_pre_ping=True` and `pool_recycle=300` to automatically recover from stale or dropped server connections.
- **Deterministic Migrations**: Database schema remains versioned and deterministic under `docs/database/001_initial_schema.sql` and `docs/database/002_seed_products.sql`.

### 3. Health & Readiness Endpoints
The platform exposes separated liveness and readiness endpoints for cloud orchestrators (Docker, Kubernetes, AWS ECS, Render, Railway):

| Endpoint | Probe Type | Purpose | Healthy Response | Unhealthy Response |
|---|---|---|---|---|
| `GET /api/health` | **Liveness** | Verifies ASGI web process is running and accepting HTTP connections. | `200 OK`<br>`{"status":"ok","service":"ai-commerce-agent-api"}` | Connection refused / Timeout |
| `GET /api/health/database` | **Readiness** | Verifies database pool can execute `SELECT 1`. Traffic should only route to instances returning 200. | `200 OK`<br>`{"status":"ok","database":"connected"}` | `503 Service Unavailable`<br>`{"status":"error","database":"disconnected","message":"..."}` |

- **Zero Secret Exposure**: Neither probe leaks database URLs, usernames, passwords, or stack traces.

### 4. Containerization (Backend Dockerfile)
- **File**: [`backend/Dockerfile`](file:///Users/roushan_iiitbgp/Desktop/AI_Agent_Ecommerce_Platform/backend/Dockerfile)
- **Base Image**: Official `python:3.12-slim` minimizing attack surface and image size.
- **Least Privilege**: Application runs under dedicated non-root user `appuser` (UID 1001).
- **Integrated Health Check**: Container includes built-in `HEALTHCHECK` probing `http://localhost:8000/api/health`.
- **Dockerignore**: Excludes `.env`, `.venv`, `*.db`, `__pycache__`, and tests from image layers.

### 5. Failure Behavior Matrix
| Failure Scenario | Runtime Behavior | Status Code | Error Masking |
|---|---|---|---|
| Database Connection Drops | Liveness stays 200, Readiness returns 503 | 503 | Masked generic error; no credentials leaked |
| Insecure/Missing Prod Secrets | Lifespan validation raises `ConfigurationError` | Fails Startup | Lists missing variable names only; zero secret leakage |
| Wildcard CORS in Prod | Lifespan validation raises `ConfigurationError` | Fails Startup | Clear guidance on requiring explicit domains |
| Brute Force / Excessive Requests | `RateLimitMiddleware` rejects client | 429 | Standard `Rate limit exceeded` header & JSON |
| Unhandled Server Exception | `unhandled_exception_handler` redacts trace | 500 | Production receives generic `Internal Server Error` |

### 6. Intentionally Deferred to Phase 18F-3
- **Frontend Containerization & Production Build Image**: Deferred to 18F-3.
- **Multi-Container Composition (`docker-compose.prod.yml`)**: Deferred to 18F-3.
- **Cloud Infrastructure & CI/CD Deployment Workflows**: Deferred to final deployment phases.



