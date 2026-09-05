# AI Commerce Agent Platform

Razorpay AI Buildathon | Track 01: AI Commerce Agent
Repository: `AI_Agent_Ecommerce_Platform` (`Roushan0012/AI-Ecommerce-Agent`)
Architectural Designation: Autonomous Commerce Engine & Agent-to-Agent Transaction Platform

---

## 1. Overview

The AI Commerce Agent Platform is an authoritative, full-stack e-commerce system built to unify conversational catalog discovery, multi-factor recommendation and growth engines, server-authoritative cart and order lifecycles, Razorpay payment processing in Test Mode, role-based JWT authentication, and a dedicated Agent-to-Agent (A2A) machine-to-machine commerce protocol. Constructed with a FastAPI backend on Python 3.12, a PostgreSQL database hosted on Supabase and managed via SQLAlchemy 2.0 ORM, and a customer storefront built with Next.js 16 (App Router), React 19, and Tailwind CSS v4, the platform enables human shoppers and autonomous software agents to transact securely and reliably.

---

## 2. Problem Statement and Solution

### The Problem
Traditional e-commerce platforms depend on rigid keyword searching, manual taxonomic browsing, and static merchandising rules. These systems fail to understand conversational user intent, cannot dynamically balance multi-factor purchasing constraints (such as real-time inventory levels and user budget proximity), and lack standardized machine-to-machine interfaces for autonomous software agents. When external software agents attempt to transact on standard web stores, they face brittle HTML scraping, insecure client-side pricing vulnerabilities, and complex payment delegation challenges.

### The Solution
The AI Commerce Agent Platform resolves these challenges through an authoritative, decoupled architecture:
- Conversational Discovery: Natural-language intent extraction translates unconstrained customer prompts into structured catalog queries with budget, category, and attribute constraints.
- Multi-Factor Scored Recommendations: A deterministic scoring algorithm balances category alignment, keyword relevance, budget proximity, and inventory health to rank products with transparent explainability rationales.
- AI Growth Engine: Context-aware upsell algorithms evaluate specification improvements within acceptable price premiums, while cross-sell algorithms use category affinity pairings to recommend companion accessories.
- Server-Authoritative Integrity: All pricing, discount logic, inventory allocations, and order state transitions are computed and verified exclusively on the backend, preventing client-side tampering.
- Dedicated Agent-to-Agent Protocol: External autonomous buyer agents authenticate via constant-time verified `X-Agent-Key` headers to programmatically discover products, check stock, assemble carts, and generate secure payment links under an untrusted-client security model.

---

## 3. High-Level Architecture

```
+---------------------------------------------------------------------------------+
|                                  CLIENTS LAYER                                  |
|                                                                                 |
|   +---------------------------------------+   +-----------------------------+   |
|   | Human Shopper Web Browser             |   | Autonomous Buyer Agent      |   |
|   | Next.js 16 (App Router) + React 19 UI |   | Machine-to-Machine REST     |   |
|   +-------------------|-------------------+   +--------------|--------------+   |
+-----------------------|--------------------------------------|------------------+
                        | HTTP / Bearer JWT                    | HTTP / X-Agent-Key
                        v                                      v
+---------------------------------------------------------------------------------+
|                         INGRESS SECURITY & GATEWAY                              |
|                                                                                 |
|   - Security Headers (HSTS, CSP, X-Frame-Options: DENY, X-Content-Type: nosniff)|
|   - Request Body Size Limiter (2MB ceiling, returns 413 Payload Too Large)      |
|   - Sliding-Window Rate Limiter (Auth: 10-30 req/min, General: 120-300 req/min) |
|   - Constant-Time Agent Key Validator (hmac.compare_digest)                     |
|   - PyJWT Bearer Authenticator (HS256) and RBAC Role Authorizer                 |
|   - Sensitive Data Redaction Filter (Scrubs credentials from logs & 422 errors) |
+---------------------------------------|-----------------------------------------+
                                        v
+---------------------------------------------------------------------------------+
|                              APPLICATION SERVICES                               |
|                                                                                 |
|   +---------------------+ +---------------------+ +---------------------------+ |
|   | AIAgentService      | | RecommendationSvc   | | GrowthRecommendationSvc   | |
|   | (Intent extraction) | | (Multi-factor score)| | (Upsell & Cross-sell)     | |
|   +---------------------+ +---------------------+ +---------------------------+ |
|   +---------------------+ +---------------------+ +---------------------------+ |
|   | CartService         | | OrderService        | | PaymentService            | |
|   | (Server pricing)    | | (Atomic lifecycle)  | | (Razorpay & webhooks)     | |
|   +---------------------+ +---------------------+ +---------------------------+ |
|   +---------------------+ +---------------------+ +---------------------------+ |
|   | AgentCommerceSvc    | | DashboardService    | | AuditService              | |
|   | (A2A discovery/cart)| | (Revenue analytics) | | (Append-only audit trail) | |
|   +---------------------+ +---------------------+ +---------------------------+ |
+---------------------------------------|-----------------------------------------+
                                        v
+---------------------------------------------------------------------------------+
|                                PERSISTENCE LAYER                                |
|                                                                                 |
|   PostgreSQL Database (Supabase) via SQLAlchemy 2.0 ORM                         |
|   Tables: users, merchants, products, carts, cart_items, orders, order_items,   |
|           payments, audit_logs                                                  |
+---------------------------------------------------------------------------------+
                                        ^
                                        | Webhook Verification (HMAC-SHA256)
                                        v
+---------------------------------------------------------------------------------+
|                            EXTERNAL PAYMENT GATEWAY                             |
|                                                                                 |
|   Razorpay Payment Gateway (Test Mode)                                          |
|   - Order Creation API (/v1/orders)                                             |
|   - Client-Side Checkout JS Modal                                               |
|   - Asynchronous Webhook Notifications (/api/payments/webhook)                  |
+---------------------------------------------------------------------------------+
```

---

## 4. Documentation Index

Complete technical documentation is organized in the [`docs/`](docs/) directory:

| Document | Focus and Technical Scope |
|---|---|
| [01. Project Overview](docs/01-project-overview.md) | Purpose, problem statement, solution, target personas, Buildathon context, and journeys |
| [02. System Architecture](docs/02-system-architecture.md) | Multi-tier architecture, system layers, communication protocols, and trust boundaries |
| [03. Database Architecture](docs/03-database.md) | PostgreSQL schema, SQLAlchemy models, constraints, relationships, and ER diagram |
| [04. AI Search & Intent](docs/04-ai-search.md) | Conversational query parsing, regex heuristics vs LLM providers, and intent schemas |
| [05. Recommendation Engine](docs/05-recommendation-engine.md) | Multi-factor scoring formula, candidate selection, ranking logic, and explainability |
| [06. Growth Engine](docs/06-growth-engine.md) | Specification-based upsell algorithms and category affinity cross-sell rules |
| [07. Cart and Orders](docs/07-cart-and-orders.md) | Authoritative cart arithmetic, transactional stock checks, and order finite state machine |
| [08. Razorpay Payments](docs/08-razorpay-payments.md) | Test Mode order creation, paise conversion, modal checkout, HMAC verification, and webhooks |
| [09. Authentication & RBAC](docs/09-authentication-and-rbac.md) | Argon2id hashing, PyJWT tokens, access control matrix, and escalation defense |
| [10. Agent-to-Agent Commerce](docs/10-agent-to-agent-commerce.md) | Machine-to-machine protocol, constant-time `X-Agent-Key`, untrusted model, and A2A APIs |
| [11. Security and Guardrails](docs/11-security-and-guardrails.md) | Defense-in-depth, rate limiting, body size limits, security headers, and secret redaction |
| [12. Audit and Observability](docs/12-audit-and-observability.md) | Relational `audit_logs` table, event classifications, immutability, and forensics |
| [13. Merchant Dashboard](docs/13-merchant-dashboard.md) | Revenue analytics, AOV, cart conversion rate, and AI revenue attribution queries |
| [14. Frontend Storefront](docs/14-frontend.md) | Next.js 16 App Router UI, 3-mode AI assistant, cart drawer, modal checkout, and receipts |
| [15. API Reference](docs/15-api-reference.md) | Comprehensive endpoint catalog with methods, paths, parameters, schemas, and status codes |
| [16. Testing Strategy](docs/16-testing.md) | 391 backend pytest tests, 94 frontend tsx tests, Newman assertions, and secret scanning |
| [17. CI/CD Pipeline](docs/17-ci-cd.md) | GitHub Actions workflow, jobs, security hardening, and failure propagation |
| [18. Docker & Deployment](docs/18-docker-and-deployment.md) | Multi-stage non-root Dockerfiles, Docker Compose orchestration, and health checks |
| [19. Environment Configuration](docs/19-environment-configuration.md) | Configuration variables reference, operating modes, and production startup assertions |
| [20. Development History](docs/20-development-history.md) | Chronological phase milestones reconstructed directly from git commit history |
| [21. Local Development](docs/21-local-development.md) | Workstation prerequisites, setup commands, Docker commands, and troubleshooting |
| [22. Limitations & Roadmap](docs/22-limitations-and-future-work.md) | Verified operational boundaries and future architectural enhancements |

---

## 5. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend Framework** | FastAPI (Python 3.12) | High-performance asynchronous REST API framework with native Pydantic v2 validation |
| **ASGI Web Server** | Uvicorn | Multi-worker ASGI web server with proxy header support |
| **Database & ORM** | PostgreSQL (Supabase) & SQLAlchemy 2.0 | Relational persistence, transactional foreign keys, check constraints, and connection pooling |
| **Database Migrations**| Alembic | Version-controlled schema migrations |
| **Password Security** | Argon2id (`argon2-cffi`) | Memory-hard password hashing resistant to GPU brute-force attacks |
| **Authentication** | PyJWT (`HS256`) | Stateless JSON Web Token issuance and role-based access control |
| **Payment Gateway** | Razorpay Python SDK | Test Mode order creation in paise and HMAC-SHA256 signature verification |
| **Rate Limiting** | Slowapi | Sliding-window in-memory rate limiting on sensitive authentication and general routes |
| **Frontend Framework** | Next.js 16.3.3 (App Router) | Server components, client hydration, route-based splitting, and Turbopack compiler |
| **UI Library** | React 19.2.8 | Declarative component architecture and client-side reactive state management |
| **Frontend Styling** | Tailwind CSS v4 | Utility-first CSS styling and responsive layout design |
| **Frontend Language** | TypeScript 5 | Strict static typing across components, API clients, and domain interfaces |
| **Backend Testing** | Pytest + pytest-asyncio + httpx | Automated unit, integration, and security regression testing (391 tests) |
| **Frontend Testing** | Node.js Test Runner + tsx | Automated unit, component, and contract testing (94 tests) |
| **API Testing** | Postman / Newman | Collection-based end-to-end API verification (35 requests, 108 assertions) |
| **Containerization** | Docker & Docker Compose | Multi-stage minimal container images running as unprivileged non-root users |
| **Continuous Integration**| GitHub Actions | Automated CI pipeline running backend tests, secret scans, and frontend builds |

---

## 6. AI Commerce and Merchandising Capabilities

### 6.1 The Three Storefront AI Modes
1. Smart Search (`ai-mode-search-btn`): Natural-language prompt search extracting intent, category constraints, budget ceilings, and attribute filters.
2. Top AI Picks (`ai-mode-recommend-btn`): Multi-factor scored recommendations evaluating candidate products across:
   $$\text{Final Score} = \min(1.0, \text{Category}_{0.30} + \text{Keywords}_{0.35} + \text{Budget}_{0.20} + \text{Inventory}_{0.15})$$
   Returns normalized match scores (e.g., `88% Match`) and transparent explainability rationales.
3. Upgrades & Accessories (`ai-mode-growth-btn`): Context-aware merchandising engine presenting:
   - Upsell: Superior alternatives in the same category within budget bounds, highlighting specification upgrades (power output, hybrid ANC, hot-swap switches).
   - Cross-Sell: Complementary accessories and companion hardware based on explicit category affinity rules (`CROSS_SELL_RULES`).

### 6.2 Agent-to-Agent (A2A) Commerce Protocol
- Secured via constant-time verified `X-Agent-Key` HTTP header using `hmac.compare_digest`.
- Untrusted Client Principle: Machine agents cannot modify prices, bypass stock constraints, or mark orders as paid.
- Machine-Readable Endpoints:
  - `POST /api/agent-commerce/discover`: Programmatic catalog discovery.
  - `GET /api/agent-commerce/products/{id}`: Authoritative specifications and live inventory.
  - `POST /api/agent-commerce/inventory/check`: Pre-flight stock availability checks.
  - `POST /api/agent-commerce/cart` & `POST /api/agent-commerce/cart/items`: Programmatic cart assembly.
  - `POST /api/agent-commerce/orders`: Idempotent order creation from cart.
  - `POST /api/agent-commerce/payments/initiate`: Razorpay payment link generation for human settlement.

---

## 7. Security and Defensive Guardrails

- Server-Authoritative Arithmetic: Client prices are strictly ignored; all subtotals and balances are derived from PostgreSQL within transactions.
- Rate Limiting: Configured via sliding windows (Auth: 10-30 req/min, Default: 120-300 req/min) returning `429 Too Many Requests`.
- Request Size Bounds: Rejects payloads exceeding 2MB (`MAX_REQUEST_BODY_BYTES`) with `413 Payload Too Large`.
- Defensive Headers: Enforces `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, and production HSTS.
- Credential Redaction: Centralized filter scrubs passwords, JWT tokens, database passwords, and API keys from logs and 422 error outputs. Generic 500 error masking in production.
- Production Assertions: Startup checks enforce minimum key lengths and forbid insecure development placeholders.

---

## 8. Verification and Quality Summary

- **Backend Test Suite**: **391 passed** in ~54s across 30 test files with 100% pass rate.
- **Frontend Test Suite**: **94 passed** in ~550ms across 11 test suites with 100% pass rate.
- **Postman / Newman Suite**: **35 requests / 108 assertions passed**.
- **Secret Leak Scan**: **Zero credentials or private keys tracked in repository**.
- **Production Build**: Next.js 16 App Router standalone compilation passes cleanly with zero TypeScript errors.

---

## 9. Local Quick Start

### Native Setup
```bash
# 1. Start Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.core.seed
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 2. Start Frontend (in separate terminal)
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

### Docker Compose Setup
```bash
# Configure backend environment
cp backend/.env.example backend/.env

# Build and start orchestrated services
docker compose up --build -d

# Verify service health
docker compose ps

# Access application
# Storefront: http://localhost:3000
# Backend API: http://localhost:8000
# OpenAPI Docs: http://localhost:8000/docs
```

---

## 10. Current Status, Scope, and Limitations

- **Current Status**: Completed through Phase 18 (Frontend Step 5.3). Verified git commit `c5fc5f3`.
- **Payment Scope**: Operates in Razorpay Test Mode with test keys. Real financial settlement requires live merchant KYC onboarding.
- **Merchant Tenancy**: Storefront interface operates as a single-merchant store; multi-vendor split cart routing is planned for future iterations.
- **AI Scope**: Intent extraction defaults to deterministic regex heuristics in `MockAIProvider` with optional OpenAI/Groq connectivity.
- **Human-in-the-Loop Settlement**: Autonomous agents generate checkout links requiring human authorization; direct automated bank debiting is deliberately not supported.

---

## 11. Author and Repository

- Author / Developer: Roushan Kumar (`Roushan0012`)
- Repository: [https://github.com/Roushan0012/AI-Ecommerce-Agent](https://github.com/Roushan0012/AI-Ecommerce-Agent)
- Track: Track 01 — AI Commerce Agent (Razorpay AI Buildathon)
