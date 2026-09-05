# Testing Strategy and Test Suites

## 1. Overview

The AI Commerce Agent Platform enforces rigorous quality assurance across all layers through automated unit tests, integration tests, security regressions, API contract validation, and build verification.

Every pull request and commit to `main` must pass all verification tiers without regressions.

---

## 2. Test Execution Summary

| Test Layer | Test Runner / Framework | Test Count | Pass Rate | Execution Time | Scope |
|---|---|---|---|---|---|
| **Backend Test Suite** | Pytest + pytest-asyncio + httpx | **391 tests** | **100%** (391/391) | ~54 seconds | Auth, catalog, AI intent, recommendations, growth, cart, orders, Razorpay, A2A, audit, security |
| **Frontend Test Suite** | Node.js Test Runner + tsx | **94 tests** | **100%** (94/94) | ~550 ms | API client, auth helpers, assistant modes, cart UI, checkout, order history, receipts |
| **Postman / Newman** | Newman Collection Runner | **35 requests / 108 assertions** | **100%** | ~15 seconds | End-to-end integration and API contract assertions |
| **Frontend Production Build**| Next.js Standalone Compiler | 1 build | Pass | ~12 seconds | Static generation, route validation, TypeScript type-checking |
| **CI Secret Scanner** | Pytest Repository Scanner | 1 test | Pass | 0.04 seconds | Full codebase scan ensuring zero tracked credentials or private keys |

---

## 3. Backend Test Suite (Pytest)

The backend test suite is located in `backend/tests/` and comprises 30 test modules executed in an isolated test environment (`ENVIRONMENT=test`).

### 3.1 Test Suite Breakdown by Functional Area

| Test Module | Tests | Focus Area |
|---|---|---|
| `test_auth_foundation.py` | 12 | Argon2id hashing, salt generation, verify mismatch, password complexity |
| `test_auth_api.py` | 15 | Registration, duplicate emails, login validation, token issuance |
| `test_auth_roles.py` | 24 | Role assignment, privilege escalation prevention, role validation |
| `test_jwt_protected_api.py` | 18 | Token decoding, expiration checks, missing/malformed auth headers |
| `test_phase17_security_final.py`| 22 | Comprehensive JWT security and cross-role permission boundary checks |
| `test_products_api.py` | 16 | Catalog listing, pagination, price range and category filters, product CRUD |
| `test_agent_api.py` | 20 | Conversational query parsing, intent extraction, category detection |
| `test_recommendation_api.py` | 16 | Multi-factor scoring calculations, weight balances, explainability rationales |
| `test_growth_api.py` | 18 | Upsell candidates, price jump bounds, cross-sell affinity rules, stock checks |
| `test_cart_order_api.py` | 25 | Cart item addition, quantity updates, inventory validation, order assembly |
| `test_payment_api.py` | 14 | Razorpay order creation, paise conversion, internal order linking |
| `test_webhook_api.py` | 22 | Webhook HMAC-SHA256 signature verification, replay protection, auto-settlement |
| `test_a2a_boundary.py` | 20 | `X-Agent-Key` constant-time verification, untrusted client model enforcement |
| `test_agent_commerce_api.py` | 18 | Machine discovery, stock checks, agent cart, idempotent order assembly |
| `test_audit_api.py` | 22 | Audit logging across operations, append-only immutability, customer ownership |
| `test_dashboard_api.py` | 18 | GMV calculation, AOV, cart conversion rate, AI attribution metrics |
| `test_security_guardrails.py` | 25 | Rate limiting sliding windows, request body limits, security headers, redaction |
| `test_adversarial_security.py` | 32 | SQL injection attempts, price tampering payloads, timing side-channels |
| `test_ci_workflow.py` | 10 | Workflow structure, failure propagation, repository-wide secret leak detection |
| `test_phase18a_config.py` | 15 | Environment settings, production assertions, insecure placeholder rejection |
| `test_phase18c_security.py` | 14 | Sliding-window rate limit tiers, 422 error credential scrubbing, 500 masking |
| `test_phase18d_frontend_contract.py` | 8 | Contract verification aligning backend endpoints with frontend TypeScript interfaces |
| `test_phase18f1_deployment_config.py`| 8 | Production deployment parameters, network host bindings, worker concurrency |
| `test_phase18f2_backend_readiness.py` | 8 | Non-root container execution, container health check probes, startup lifecycle |
| `test_phase18f3_orchestration.py` | 8 | Multi-container Compose service dependencies, internal networking, health probes |
| `test_phase18f4_production_smoke.py` | 10 | Production smoke verification, database check endpoint, security headers |
| `test_models.py` | 14 | Declarative SQLAlchemy models, foreign keys, cascade rules, check constraints |
| `test_database_health.py` | 4 | PostgreSQL connectivity check, error handling during connection drop |
| `test_health.py` | 2 | `/api/health` liveness endpoint verification |
| `test_seed.py` | 5 | Deterministic database seeding for catalog merchandise |

### 3.2 Running Backend Tests
```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

---

## 4. Frontend Test Suite (Node.js Test Runner / TSX)

The frontend test suite is located in `frontend/tests/` and executes using Node.js's built-in test runner combined with `tsx` (`npx tsx --test "tests/**/*.test.ts"`).

### 4.1 Test Modules
1. `add_to_cart.test.ts` (10 tests): Authenticated Add-to-Cart pipeline, inventory boundary warnings, cart drawer updates.
2. `ai_assistant.test.ts` (10 tests): Natural-language prompt submission, query sanitization, category tag filtering.
3. `cart_ui_and_sync.test.ts` (10 tests): Quantity adjustment, item removal, server-authoritative subtotal and total rendering.
4. `checkout_razorpay.test.ts` (10 tests): Order conversion trigger, Razorpay modal options injection, authorization callbacks.
5. `customer_orders_api.test.ts` (8 tests): API client order history retrieval, receipt data mapping, error states.
6. `growth_ui.test.ts` (10 tests): Growth mode toggle, upsell card rendering, cross-sell companion recommendations, Add-to-Cart synchronization.
7. `order_history_ui.test.ts` (10 tests): Order history listing, status badge styling, receipt modal drill-down, back navigation.
8. `phase18d.test.ts` (9 tests): JWT storage in `localStorage`, token expiration detection, automatic 401 logout, machine key isolation.
9. `product_detail_modal.test.ts` (5 tests): Modal open/close actions, image preview, JSONB attribute rendering.
10. `product_images.test.ts` (2 tests): Image fallback handling, aspect ratio styling.
11. `recommendations_ui.test.ts` (10 tests): Top AI Picks mode toggle, score percentage derivation, explainability rationale tags.

### 4.2 Running Frontend Tests
```bash
cd frontend
npm test
```

---

## 5. Postman / Newman API Collection

The repository includes a comprehensive Postman collection in `docs/postman/AI-Commerce-Agent-API.postman_collection.json`.

### Verification Scope
- 35 individual HTTP requests executed sequentially.
- 108 automated assertions checking:
  - HTTP status codes (`200 OK`, `201 Created`, `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`).
  - Response JSON schemas and mandatory fields.
  - Mathematical balance verification (authoritative subtotals and totals).
  - Webhook signature validation.
  - Constant-time `X-Agent-Key` machine authentication.

### Running Newman Locally
```bash
npx newman run docs/postman/AI-Commerce-Agent-API.postman_collection.json
```

---

## 6. Build and Infrastructure Verification

### 6.1 Next.js Production Build
Validates that all React components, App Router pages, and TypeScript definitions compile cleanly without errors:
```bash
cd frontend
npm run build
```

### 6.2 Docker Build and Compose Verification
Validates that multi-stage Docker builds complete successfully, produce minimal images, and run as unprivileged users:
```bash
docker compose build
docker compose up -d
docker compose ps
docker compose down
```

---

## 7. Security and Secret Leak Prevention Testing

The test `test_repository_wide_secret_leak_prevention` in `backend/tests/test_ci_workflow.py` executes during every CI run:
- Recursively inspects all tracked files in the repository.
- Flags any occurrences of private API keys, live JWT secrets, live database credentials, or real Razorpay secrets.
- Verifies that `.env` and `.env.local` files are ignored by `.gitignore`.
- Ensures zero credentials are leaked to version control.
