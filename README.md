# AI Commerce Agent Platform

> Razorpay AI Buildathon — Track 01: AI Commerce Agent

A production-grade, authoritative e-commerce backend and merchant platform powered by FastAPI, PostgreSQL (Supabase), Razorpay Test Mode payments, security guardrails, an observable audit trail, and an **Agent-to-Agent Commerce** machine-to-machine interface.

---

## Architecture Overview

```
Buyer Agent / Frontend
        ↓
FastAPI Router Gateway
        ↓
Authentication & Guardrails (Phase 12, Phase 15)
        ↓
Core Services (AI Intent, Catalog Search, Recommendations, Cart, Orders, Razorpay)
        ↓
PostgreSQL Database (Transactional Storage & Phase 13 Audit Trail)
        ↓
Phase 14 Merchant Dashboard (Real-Time Analytics & Growth Metrics)
```

---

## Phase Implementation Status

| Phase | Description | Status |
|---|---|---|
| **Phase 2** | FastAPI ↔ Supabase PostgreSQL Connection & Schema | **Complete** |
| **Phase 3** | Product Catalog & Deterministic Seeding | **Complete** |
| **Phase 4** | Semantic & Filtered Product Discovery APIs | **Complete** |
| **Phase 5** | AI Agent Intent Extraction (Mock, OpenAI, Groq) | **Complete** |
| **Phase 6** | AI Intent → Catalog Search & Tools | **Complete** |
| **Phase 7** | Multi-factor Recommendation Engine with Ranking | **Complete** |
| **Phase 8** | Growth Engine: Upsell & Cross-sell Recommendations | **Complete** |
| **Phase 9** | Cart & Order Management Foundation | **Complete** |
| **Phase 10** | Razorpay Payment Integration (Test Mode) | **Complete** |
| **Phase 11** | Razorpay Webhook Signature Verification & Auto-Settlement | **Complete** |
| **Phase 12** | Security & Backend-Authoritative Guardrails | **Complete** |
| **Phase 13** | Observable Agent Audit Trail & Secret Redaction | **Complete** |
| **Phase 14** | Merchant Dashboard & Real-Time Business Analytics | **Complete** |
| **Phase 15** | Agent-to-Agent Commerce (Machine-to-Machine Interface) | **Complete** |
| **Phase 16** | Adversarial Security Regression Suite & Verification | **Complete** |
| **Phase 17A** | JWT Authentication Foundation & Argon2 Hashing | **Complete** |
| **Phase 17B** | User Registration & Login Endpoints | **Complete** |
| **Phase 17C** | JWT Protected APIs & Ownership Verification | **Complete** |
| **Phase 18A** | Production Configuration & Environment Hardening | **Complete** |
| **Phase 18B-1** | GitHub Actions CI Foundation Pipeline | **Complete** |
| **Phase 18B-2** | CI/CD Quality & Failure-Safety Hardening | **Complete** |
| **Phase 18C** | API & Application Hardening | **Complete** |
| **Phase 18D** | Frontend Production Configuration | **Complete** |
| **Phase 18E** | CI/CD Pipeline Validation & Testing | **Complete** |

---

## Key Features

### 1. Agent-to-Agent Commerce (Phase 15)
- **Machine-to-Machine Security**: Protected by `X-Agent-Key` header verified in constant time.
- **Untrusted External Agent Model**: Client-provided prices, subtotals, and totals are ignored; all calculations and inventory validations are backend-authoritative.
- **Idempotency**: Repeated checkout requests with the same cart return the existing order safely without duplicate conversions.
- **Payment Boundary**: External agents cannot mark orders as paid; payment confirmation strictly requires HMAC-SHA256 verified Razorpay webhooks.

### 2. Guardrails & Audit Trail (Phases 12 & 13)
- Centralized validation across all sensitive endpoints.
- Redaction of API keys, tokens, and credentials in logs and outputs.
- Comprehensive tracking of `AGENT_REQUEST`, `RECOMMENDATION`, `CART_UPDATED`, `ORDER_CREATED`, and `PAYMENT_EVENT`.

### 3. Merchant Dashboard (Phase 14)
- Real-time revenue, order counts, cart conversion rate, and average order value (AOV).
- AI attribution metrics and growth revenue tracking (upsell and cross-sell).
- Live observable audit feed and order status breakdown.

### 4. API & Application Hardening (Phase 18C)
- **In-Memory Rate Limiting**: Multi-tier sliding-window rate limiting (`auth` and `default` tiers) returning standard `429 Too Many Requests` with `Retry-After` headers.
- **Request Size & Input Protections**: Configurable body payload limits (`MAX_REQUEST_BODY_BYTES`, default 2MB) with immediate `413 Payload Too Large` responses and strict string length bounds on credentials and queries.
- **Defensive Security Headers**: Comprehensive HTTP protection (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Referrer-Policy`, `Permissions-Policy`, and production `Strict-Transport-Security`).
- **Error Handling & Information Disclosure**: Sensitive fields (passwords, tokens, keys) automatically redacted from `422` validation responses; generic masked responses for unhandled `500` server errors in production.
- **Secret-Free Logging**: Automated `SensitiveDataRedactionFilter` scrubbing passwords, JWTs, Bearer tokens, API keys, and database passwords from all loggers.

### 5. Frontend Production Configuration & Authentication (Phase 18D)
- **Centralized API Base URL**: Driven by `NEXT_PUBLIC_API_BASE_URL` with local development fallback (`http://127.0.0.1:8000`), allowing external backend binding without code edits.
- **Client-Side JWT Management**: Secure `localStorage` access token caching with automatic expiry detection and reactive UI state synchronization.
- **Authenticated Request Layer**: Protected API requests inject `Authorization: Bearer <access_token>`; `401 Unauthorized` automatically purges expired client tokens.
- **Role-Aware UI Convenience**: UI dynamically adapts for `customer`, `merchant`, and `admin` roles, backed by strict server-side RBAC validation.
- **Machine Key Isolation**: Frontend code strictly decoupled from `COMMERCE_AGENT_KEY` / `X-Agent-Key` and backend secrets.

---

## Running the Platform

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Running Test Suites
```bash
# Frontend Tests (9 automated unit/contract tests)
cd frontend && npm test

# Backend Tests (358 tests across all phases)
backend/.venv/bin/pytest backend/tests/ -v

# Postman / Newman (35 live endpoint tests / 108 assertions)
npx newman run docs/postman/AI-Commerce-Agent-API.postman_collection.json
```

---

## Continuous Integration (CI/CD Pipeline)

The repository includes an automated GitHub Actions CI pipeline defined in [.github/workflows/ci.yml](.github/workflows/ci.yml).

### When It Runs
- **Pushes** targeting the `main` branch.
- **Pull Requests** targeting the `main` branch.
- **Manual Trigger** (`workflow_dispatch`) for on-demand verification.
- **Concurrency Cancellation**: Superseded pull request runs are automatically canceled to conserve runner resources while keeping full history on `main`.

### Security Hardening & Permissions
- **Principle of Least Privilege**: CI runs with `permissions: contents: read` to prevent unauthorized repository write access.
- **Zero Secrets Required**: The pipeline relies entirely on isolated test/development defaults and mock providers. No production credentials, Supabase database URLs, or Razorpay live keys are configured or exposed in CI.
- **No Artifact Leakage**: No `.env` files, build caches, or credentials are saved or published as artifacts.
- **Secrets Protection**: Production `.env` and `.env.local` files are ignored by git and never committed or printed in CI logs.

### What It Validates
1. **Backend Test Suite (`backend-tests`)**:
   - Sets up Python 3.12 with pip dependency caching based on `backend/requirements.txt`.
   - Installs locked backend dependencies via `pip install -r backend/requirements.txt`.
   - Executes the complete backend pytest suite (`pytest -v`) in isolated test mode (`ENVIRONMENT=test`).
   - Runs automated repository-wide secret leak scanning (`test_repository_wide_secret_leak_prevention`) ensuring zero committed credentials.
   - Ensures all domain models, JWT authentication, RBAC, Agent-to-Agent boundaries, Razorpay webhooks, and security guardrails pass without regressions.
2. **Frontend Test & Production Build (`frontend-build`)**:
   - Sets up Node.js 20 with npm dependency caching based on `frontend/package-lock.json`.
   - Installs locked frontend dependencies via clean `npm ci`.
   - Executes `npm test` verifying client-side authentication, auth headers, token expiration, and secret boundary isolation.
   - Executes `npm run build` with telemetry disabled (`NEXT_TELEMETRY_DISABLED=1`, `CI=true`) to verify Next.js compilation, TypeScript type-checking, and static page generation.

### What CI Does NOT Do
- **No Cloud Deployment**: CI only validates code correctness, test suites, and buildability; deployment to cloud providers or container registries is out of scope for Phase 18E and handled in future deployment phases.
- **No Production Secrets**: CI never connects to live databases, production Razorpay instances, or external LLM APIs.

### Failure Safety & Propagation
- **Strict Exit Codes**: All commands run under explicit bash shell defaults (`-eo pipefail`); command errors are never swallowed with `continue-on-error` or shell fallbacks.
- **Independent Diagnostics**: Backend test failures and frontend test/build failures report distinctly in the GitHub Actions UI.

### Troubleshooting CI Failures
When a CI run fails, developers should check:
1. **Backend Test Failures**:
   - Reproduce locally: `backend/.venv/bin/pytest backend/tests/ -v`
   - Verify all model schemas, route handlers, or security guardrails conform to existing specifications.
   - Ensure new code does not rely on local `.env` variables without providing safe test defaults in `Settings`.
2. **Frontend Test Failures**:
   - Reproduce locally: `cd frontend && npm test`
   - Check unit/contract assertions for token storage, auth headers, and secret isolation.
3. **Frontend Build Failures**:
   - Reproduce locally: `cd frontend && npm ci && npm run build`
   - Check for TypeScript compile errors, missing typings, or broken imports.
   - Verify environment variable references use `NEXT_PUBLIC_` prefixes when required on the client side.
