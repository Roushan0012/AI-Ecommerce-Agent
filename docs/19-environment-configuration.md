# Environment Configuration and Secret Management

## 1. Overview

The AI Commerce Agent Platform follows the Twelve-Factor App methodology by strictly separating configuration from code. Configuration is injected via environment variables loaded from `.env` files in local development or passed directly by container runtimes in production.

Templates are maintained in:
- `backend/.env.example`
- `frontend/.env.example`

> **Security Rule**: Real credentials, private keys, database passwords, or JWT secrets must never be committed to version control. `.env`, `.env.local`, and related secrets files are explicitly ignored by `.gitignore`.

---

## 2. Backend Environment Variables (`backend/.env.example`)

| Variable Name | Required | Default / Example | Description |
|---|---|---|---|
| `ENVIRONMENT` | Yes | `development` | Operating mode: `development`, `test`, or `production`. |
| `DEBUG` | No | `true` (dev) / `false` (prod) | FastAPI debug mode. Unconditionally forced to `false` in production. |
| `HOST` | No | `127.0.0.1` (dev) / `0.0.0.0` (prod)| Server network interface binding. |
| `PORT` | No | `8000` | Port on which the FastAPI ASGI server listens. |
| `WEB_CONCURRENCY` | No | `1` (dev) / `4` (prod) | Number of worker processes spawned by Uvicorn. |
| `CORS_ORIGINS` | Yes | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated or JSON list of allowed origins. Wildcard `*` forbidden in production. |
| `DATABASE_URL` | Yes | `postgresql://user:pass@host:5432/db` | PostgreSQL connection string. In production, SQLite is rejected. |
| `SUPABASE_URL` | No | `https://[project-ref].supabase.co` | Supabase project URL. |
| `SUPABASE_PUBLISHABLE_KEY`| No | `anon-key` | Supabase publishable client key. |
| `AI_PROVIDER` | No | `mock` | Intent extraction backend: `mock`, `openai`, `groq`, `openrouter`. |
| `AI_MODEL` | No | `gpt-4o-mini` | Model identifier used when an external LLM provider is active. |
| `AI_API_KEY` | No | Empty | API key for OpenAI, Groq, or OpenRouter (optional if `AI_PROVIDER=mock`). |
| `AI_BASE_URL` | No | Empty | Base URL for OpenAI-compatible REST API endpoints. |
| `RAZORPAY_KEY_ID` | Yes | `rzp_test_placeholder` | Razorpay public key ID. Must be set to valid test/live key in production. |
| `RAZORPAY_KEY_SECRET` | Yes | Empty | Razorpay private secret key used for HMAC signature generation. |
| `RAZORPAY_CURRENCY` | No | `INR` | Standard three-letter ISO currency code. |
| `RAZORPAY_WEBHOOK_SECRET`| Yes | Empty | Secret used to verify incoming `X-Razorpay-Signature` webhook headers. |
| `COMMERCE_AGENT_KEY` | Yes | Empty | Shared secret for machine-to-machine Agent-to-Agent API authentication. Min 16 chars. |
| `JWT_SECRET_KEY` | Yes | Empty | Cryptographic secret used for signing JWT bearer tokens. Min 32 chars in production. |
| `JWT_ALGORITHM` | No | `HS256` | Cryptographic algorithm for JWT signing. |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Duration in minutes before issued JWT tokens expire. |
| `RATE_LIMIT_ENABLED` | No | `true` | Enables or disables sliding-window rate limiting. |
| `RATE_LIMIT_AUTH_PER_MINUTE` | No | `30` (dev) / `10` (prod) | Maximum requests per minute per IP on authentication routes. |
| `RATE_LIMIT_DEFAULT_PER_MINUTE` | No | `300` (dev) / `120` (prod) | Maximum requests per minute per IP on general routes. |
| `MAX_REQUEST_BODY_BYTES` | No | `2097152` (2MB) | Maximum permitted incoming HTTP request body size in bytes. |
| `SECURITY_HEADERS_ENABLED` | No | `true` | Enables injection of defensive HTTP headers (CSP, HSTS, X-Frame-Options). |

---

## 3. Frontend Environment Variables (`frontend/.env.example`)

| Variable Name | Required | Default / Example | Description |
|---|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Yes | `http://127.0.0.1:8000` | Fully qualified base URL pointing to the running backend service. |
| `NEXT_PUBLIC_RAZORPAY_KEY_ID` | Yes | `rzp_test_placeholder` | Public Razorpay key ID passed to the client-side Razorpay Checkout modal. |

> **Security Warning**: Only variables prefixed with `NEXT_PUBLIC_` are exposed to the client browser bundle. Never place `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `JWT_SECRET_KEY`, `COMMERCE_AGENT_KEY`, or `DATABASE_URL` in frontend environment files.

---

## 4. Environment Operating Modes

The system behaves differently across three distinct runtime environments:

```
+-------------------------------------------------------------------------------+
|                        ENVIRONMENT OPERATING MODES                            |
+----------------------+-----------------------+--------------------------------+
| Mode: development    | Mode: test            | Mode: production               |
+----------------------+-----------------------+--------------------------------+
| - Host: 127.0.0.1    | - Host: In-process    | - Host: 0.0.0.0                |
| - Debug: true        | - Debug: false        | - Debug: false (forced)        |
| - Concurrency: 1     | - Concurrency: 1      | - Concurrency: 4 workers       |
| - Mock defaults OK   | - SQLite in-memory OK | - Insecure placeholders barred |
| - Open CORS origins  | - Rate limits relaxed | - CORS origin whitelist enforced|
| - Error traces shown | - Deterministic mocks | - Error traces masked (500)    |
|                      |                       | - HSTS header enabled          |
+----------------------+-----------------------+--------------------------------+
```

---

## 5. Startup Validation in Production (`validate_production_config()`)

When `ENVIRONMENT=production`, the application executes `Settings.validate_production_config()` during FastAPI startup. The server will abort with `ConfigurationError` if any of the following conditions are met:
1. `DATABASE_URL` is missing or contains `"sqlite"`. Production requires managed PostgreSQL.
2. `JWT_SECRET_KEY` matches the development placeholder or has fewer than 32 characters.
3. `COMMERCE_AGENT_KEY` matches development placeholders or has fewer than 16 characters.
4. `RAZORPAY_KEY_ID` matches `rzp_test_placeholder`.
5. `RAZORPAY_KEY_SECRET` is missing.
6. `RAZORPAY_WEBHOOK_SECRET` matches development placeholders or is empty.
7. `CORS_ORIGINS` contains a wildcard (`*`) while credentials are enabled.

---

## 6. Local Setup Instructions

### Backend Configuration
```bash
cd backend
cp .env.example .env
# Edit .env to supply your local or Supabase PostgreSQL connection string
```

### Frontend Configuration
```bash
cd frontend
cp .env.example .env.local
# Set NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```
