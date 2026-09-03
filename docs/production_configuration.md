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
