# System Architecture

## 1. Architectural Overview

The AI Commerce Agent Platform is organized as a multi-tier, decoupled architecture designed around strict separation of concerns, defensive security perimeters, and backend authority. The system separates the presentation layer from business logic and database persistence, ensuring that all pricing, inventory modifications, order states, and payment verifications remain under server control.

```
+-----------------------------------------------------------------------------------------+
|                                     CLIENTS LAYER                                       |
|                                                                                         |
|   +---------------------------------------------+   +-------------------------------+   |
|   |         Human Shopper Web Browser           |   |   External Autonomous Agent   |   |
|   |   Next.js 16 (App Router) + React 19 Client |   |     Machine-to-Machine REST   |   |
|   |       Tailwind CSS v4 Storefront UI         |   |         Buyer Agent           |   |
|   +---------------------------------------------+   +-------------------------------+   |
+--------------------------|------------------------------------------|-------------------+
                           | HTTP / JSON                              | HTTP / JSON
                           | Bearer JWT (Optional/Customer)           | X-Agent-Key Header
                           v                                          v
+-----------------------------------------------------------------------------------------+
|                            INGRESS GATEWAY & SECURITY BOUNDARY                          |
|                                                                                         |
|   +---------------------------------------------------------------------------------+   |
|   | SecurityHeadersMiddleware: HSTS, X-Frame-Options, CSP, X-Content-Type-Options    |   |
|   | RequestSizeLimitMiddleware: Rejects bodies > MAX_REQUEST_BODY_BYTES (2MB)       |   |
|   | RateLimitMiddleware: Sliding-window limits (Auth: 10/30/min, Default: 120/300) |   |
|   | CORSMiddleware: Validates origin whitelist (Wildcard forbidden in production)   |   |
|   | AgentKeyValidator: Constant-time comparison (hmac.compare_digest)                |   |
|   | JWTAuthenticator: PyJWT HS256 verification and RBAC role extraction             |   |
|   | SensitiveDataRedactionFilter: Scrubs secrets from logs and 422 error outputs     |   |
|   +---------------------------------------------------------------------------------+   |
+------------------------------------------|----------------------------------------------+
                                           v
+-----------------------------------------------------------------------------------------+
|                                   FASTAPI APPLICATION LAYER                             |
|                                                                                         |
|   +---------------------------------------------------------------------------------+   |
|   | API Routers (/api/*):                                                           |   |
|   | - /api/auth             - /api/products         - /api/cart                     |   |
|   | - /api/orders           - /api/payments         - /api/agent                    |   |
|   | - /api/agent-commerce   - /api/dashboard        - /api/audit                    |   |
|   | - /api/admin            - /api/health                                           |   |
|   +---------------------------------------------------------------------------------+   |
|                                          |                                              |
|                                          v                                              |
|   +---------------------------------------------------------------------------------+   |
|   | Core Business Services:                                                         |   |
|   | +-----------------------+ +-----------------------+ +-------------------------+ |   |
|   | |  AIAgentService       | | RecommendationService | | GrowthRecommendationSvc | |   |
|   | |  - Intent extraction  | | - Multi-factor score  | | - Upsell engine         | |   |
|   | |  - Query sanitization | | - Candidate ranking   | | - Cross-sell engine     | |   |
|   | +-----------------------+ +-----------------------+ +-------------------------+ |   |
|   | +-----------------------+ +-----------------------+ +-------------------------+ |   |
|   | |  CartService          | | OrderService          | | PaymentService          | |   |
|   | |  - Stock validation   | | - Atomic checkout     | | - Razorpay order create | |   |
|   | |  - Server pricing     | | - State machine       | | - Webhook processor     | |   |
|   | +-----------------------+ +-----------------------+ +-------------------------+ |   |
|   | +-----------------------+ +-----------------------+ +-------------------------+ |   |
|   | |  AgentCommerceService | | DashboardService      | | AuditService            | |   |
|   | |  - A2A discovery      | | - Revenue analytics   | | - Append-only logging   | |   |
|   | |  - Idempotent orders  | | - AI attribution      | | - Event redaction       | |   |
|   | +-----------------------+ +-----------------------+ +-------------------------+ |   |
|   +---------------------------------------------------------------------------------+   |
+------------------------------------------|----------------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------------+
|                                    PERSISTENCE LAYER                                    |
|                                                                                         |
|   PostgreSQL Database (Supabase) via SQLAlchemy 2.0 ORM Engine                          |
|   Connection Pool: QueuePool with SSL enforcement and schema migrations (Alembic)       |
|   Tables:                                                                               |
|   - users          - products       - carts          - cart_items                       |
|   - orders         - order_items    - payments       - audit_logs    - merchants        |
+-----------------------------------------------------------------------------------------+
                                           ^
                                           | Webhook Notifications (HMAC-SHA256)
                                           v
+-----------------------------------------------------------------------------------------+
|                                EXTERNAL PAYMENT GATEWAY                                 |
|                                                                                         |
|   Razorpay Payment Gateway (Test Mode)                                                  |
|   - Order API (POST https://api.razorpay.com/v1/orders)                                 |
|   - Checkout JS Client Modal (Cards, Netbanking, UPI simulation)                        |
|   - Asynchronous Webhook Service (POST /api/payments/webhook)                           |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Architectural Layers

### 2.1 Presentation Layer (Frontend)
- Framework: Next.js 16.3.3 utilizing App Router and React 19.2.8.
- Bundler: Turbopack for compilation and development hot reload.
- Styling: Tailwind CSS v4 with zero-runtime utility classes.
- Language: TypeScript 5 offering strict static typing across all interfaces and API response models.
- Rendering Strategy: Server components provide initial catalog page structure; dynamic client components manage interactive elements (AI assistant drawer, cart side drawer, payment modal, order receipt drill-downs).
- State Synchronization: Client-side authentication token stored in `localStorage` with automatic token expiration detection (`isTokenExpired`) and reactive broadcast across components.

### 2.2 Ingress and Security Gateway
Every inbound HTTP request traverses centralized security middleware before reaching route handlers:
- `SecurityHeadersMiddleware`: Injects protective HTTP response headers:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: geolocation=(), camera=(), microphone=()`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (in production mode)
- `RequestSizeLimitMiddleware`: Inspects `Content-Length` headers and rejects payloads exceeding `MAX_REQUEST_BODY_BYTES` (default: 2MB) with `413 Payload Too Large`.
- `RateLimitMiddleware`: Enforces sliding-window in-memory rate limiting across IP addresses. Authentication endpoints are throttled to 10-30 requests per minute; default endpoints allow 120-300 requests per minute.
- `CORSMiddleware`: Restricts cross-origin requests to configured domains (`CORS_ORIGINS`). In production mode, wildcard origins (`*`) are explicitly rejected if credentials are enabled.

### 2.3 Application Layer (FastAPI)
The backend application is structured around FastAPI on Python 3.12, managed by the Uvicorn ASGI server with configurable multi-worker concurrency (`WEB_CONCURRENCY`).
- Router Organization: 11 distinct routers registered in `app/main.py`:
  - `auth_router`: Registration, login, profile inspection (`/api/auth/*`).
  - `products_router`: Product catalog query and CRUD operations (`/api/products/*`).
  - `agent_router`: Human-facing conversational search, recommendations, and growth suggestions (`/api/agent/*`).
  - `cart_router`: Persistent cart operations and item management (`/api/cart/*`).
  - `orders_router`: Order creation, history, and receipt retrieval (`/api/orders/*`).
  - `payments_router`: Razorpay order creation and webhook verification (`/api/payments/*`).
  - `agent_commerce_router`: Machine-to-machine commerce for autonomous agents (`/api/agent-commerce/*`).
  - `dashboard_router`: Merchant revenue metrics and activity feed (`/api/dashboard/*`).
  - `audit_router`: Relational audit trail inspection (`/api/audit/*`).
  - `admin_router`: Administrative system health and metrics (`/api/admin/*`).
  - Health endpoints: Liveness and database connectivity probes (`/api/health`, `/api/health/database`).

### 2.4 AI and Merchandising Engines
- AI Intent Service (`AIAgentService`):
  - Pluggable provider architecture (`MockAIProvider`, `OpenAICompatibleProvider`).
  - The default configuration uses `MockAIProvider`, executing deterministic regex parsing to extract category, price bounds, and keywords without external network calls or latency.
  - Optional LLM integration supports OpenAI, Groq, or OpenRouter via `AI_PROVIDER` and `AI_API_KEY`.
- Recommendation Engine (`RecommendationService`):
  - Filters candidate products adhering to hard constraints (active status, stock availability, budget bounds).
  - Calculates a composite score (0.0 to 1.0) using deterministic weights: category alignment (30%), keyword relevance (35%), price proximity (20%), and inventory health (15%).
  - Generates transparent, human-readable rationale strings.
- Growth Engine (`GrowthRecommendationService`):
  - Upsell Module: Finds same-category items with superior attributes costing more than the reference item, enforcing budget boundaries and inventory health.
  - Cross-Sell Module: Employs explicit category affinity mappings (`CROSS_SELL_RULES`) linking primary categories to companion accessory SKUs with pre-computed affinity weights and contextual rationale templates.

### 2.5 Commerce and Transaction Layer
- Cart Service (`CartService`): Validates stock availability against the database, creates or retrieves user-scoped carts, and recalculates authoritative subtotals and discounts.
- Order Service (`OrderService`): Atomically converts cart items into order snapshots, captures immutable unit prices, transitions cart status to `converted`, and logs audit events.
- Payment Service (`PaymentService`): Initiates Razorpay orders in INR paise, reconciles currency and amounts, processes incoming webhooks, and transitions order status to `paid`.

### 2.6 Persistence Layer
- Database Engine: PostgreSQL 15+ hosted on Supabase.
- ORM: SQLAlchemy 2.0 with declarative mapped columns, typed relationships, and cascading rules.
- Connection Management: SQLAlchemy `QueuePool` utilizing SSL mode (`sslmode=require`) for encrypted database transport.
- Migrations: Alembic migrations tracking schema revisions deterministically.

### 2.7 External Services
- Razorpay Payment Gateway: Test Mode REST API handles order registration (`/v1/orders`). Webhook callbacks notify the backend upon successful payment capture (`payment.captured`, `order.paid`).

---

## 3. Architectural Boundaries and Trust Model

```
+--------------------------+-------------------------------------------------------------+
| Boundary                 | Trust & Enforcement Policy                                  |
+--------------------------+-------------------------------------------------------------+
| Browser -> Backend       | UNTRUSTED. All inputs validated with Pydantic. Pricing and  |
|                          | cart calculations are strictly server-authoritative.       |
+--------------------------+-------------------------------------------------------------+
| External Agent -> Backend| UNTRUSTED. Authenticated via constant-time X-Agent-Key.    |
|                          | Cannot override prices, mark orders paid, or bypass stock.  |
+--------------------------+-------------------------------------------------------------+
| Backend -> Database      | TRUSTED INTERNAL. Uses parameterized SQLAlchemy queries to   |
|                          | eliminate SQL injection. Connection secured via SSL.        |
+--------------------------+-------------------------------------------------------------+
| Razorpay -> Backend      | UNTRUSTED UNTIL VERIFIED. Inbound webhooks require valid    |
| (Webhook Boundary)       | HMAC-SHA256 signature in X-Razorpay-Signature header.       |
+--------------------------+-------------------------------------------------------------+
```

### 3.1 Server-Authoritative Boundary
Under no circumstances does the backend accept unit prices, line totals, or discount calculations submitted by client applications or external agents. The client specifies only the target `product_id` and desired `quantity`. The backend retrieves the current `Product.price` and `Product.inventory` from the database within a transaction, computing all financial figures independently.

### 3.2 Payment State Boundary
An order can transition to `paid` status through only two mechanisms:
1. Validated Razorpay client signature verification (`POST /api/payments/verify`) where HMAC-SHA256 signature matches `razorpay_order_id` and `razorpay_payment_id`.
2. Validated Razorpay webhook execution (`POST /api/payments/webhook`) where `X-Razorpay-Signature` is verified against `RAZORPAY_WEBHOOK_SECRET` and the transaction amount matches the authoritative database balance.
Neither shoppers, merchants, nor external autonomous agents possess permissions to mark an order as paid directly.
