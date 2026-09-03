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

## 6. Continuous Integration (CI) Security

The automated GitHub Actions CI pipeline ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)) runs on pushes and pull requests targeting `main`.
- **Zero Production Secrets in CI**: CI runs with `ENVIRONMENT=test` and an isolated SQLite test database. Production credentials, Supabase database URLs, and live payment keys are not stored in GitHub repository secrets or accessed in CI runs.
- **Production Guardrail Integrity**: CI validates that all unit tests and security regression tests pass without weakening production validation safeguards.

