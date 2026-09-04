# AI Commerce Agent: Autonomous and Agent-to-Agent E-Commerce Platform

Razorpay AI Buildathon | Track 01: AI Commerce Agent

A production-grade, full-stack autonomous e-commerce platform featuring a FastAPI backend, PostgreSQL relational persistence, Razorpay payment processing (Test Mode), multi-factor recommendation and growth engines, role-based JWT authentication, security guardrails, an observable audit trail, an Agent-to-Agent (A2A) machine-to-machine commerce protocol, and a responsive Next.js 16 storefront.

---

## 1. Project Title

- Application Name: AI Commerce Agent Platform
- Repository: `AI_Agent_Ecommerce_Platform` (`Roushan0012/AI-Ecommerce-Agent`)
- Architectural Designation: Autonomous Commerce Engine & Agent-to-Agent Transaction Platform

---

## 2. Project Overview

### Problem Statement
Traditional e-commerce platforms depend heavily on static keyword search, rigid taxonomic navigation, and manual rule-based merchandising. These mechanisms fail to capture nuanced natural-language customer intent, cannot balance multi-factor purchasing constraints such as real-time inventory and customer review ratings, and lack automated mechanisms to recommend relevant upsell alternatives or cross-sell companions. Furthermore, as autonomous AI agents emerge to assist human shoppers or conduct procurement on behalf of organizations, traditional storefronts lack secured, standardized, machine-to-machine interfaces that allow external agents to discover products, assemble carts, and execute commercial transactions programmatically without exposing payment credentials or compromising server authority.

### Solution
The AI Commerce Agent Platform addresses these challenges by unifying conversational natural-language catalog discovery, multi-factor recommendation algorithms, and an autonomous Agent-to-Agent (A2A) commerce protocol within an authoritative, full-stack architecture:
- **Conversational Catalog Discovery**: Parses unconstrained shopper queries to extract intent, category constraints, budget ceilings, and desired product attributes.
- **Scored Multi-Factor Recommendations**: Balances semantic relevance, budget fit, stock availability, and review ratings into a composite score with human-readable explainability rationales.
- **AI Growth Engine**: Dynamically identifies category-specific upsell alternatives (higher-tier specifications within a bounded price premium) and cross-sell companion items (accessories, complementary hardware) to drive Average Order Value (AOV).
- **Server-Authoritative Commerce**: Retains strict backend authority over pricing, discount calculations, inventory validation, order status transitions, and payment settlement.
- **Agent-to-Agent (A2A) Interface**: Provides dedicated machine-readable endpoints authenticated via constant-time verified agent keys, allowing external autonomous software agents to transact safely on behalf of users.
- **Modern Responsive Storefront**: Built on Next.js 16 App Router, React 19, and Tailwind CSS v4, providing an interactive AI Shopping Assistant, slide-out cart drawer, Razorpay checkout modal, and customer order history.

### End-to-End Customer Journey
1. **Discovery**: The shopper enters a natural-language query in the AI Shopping Assistant (e.g., "High-performance gaming laptop under 90000 with 16GB RAM").
2. **Intent Parsing & Search**: The backend classifies intent, extracts budget bounds, identifies target categories, and queries catalog items meeting the criteria.
3. **Recommendation & Explainability**: The recommendation engine scores matching products across four weighted dimensions and presents ranked items alongside transparent rationale tags.
4. **Growth Suggestions**: The shopper views contextual upsell alternatives (e.g., premium tier with 32GB RAM and 1TB SSD) and companion accessories (e.g., protective sleeve, gaming mouse).
5. **Cart Synchronization**: Adding items to the cart performs real-time transactional inventory validation against the PostgreSQL database.
6. **Checkout & Payment**: The customer initiates checkout, creating a server-authoritative order in `pending_payment` status. The frontend opens the Razorpay Checkout modal in Test Mode.
7. **Settlement & Stock Decrement**: Upon payment authorization, the backend cryptographically verifies the payment signature (or webhook), transitions the order status to `paid`, decrements product inventory, and clears the cart.
8. **Receipt & History**: The customer accesses their authenticated order history, viewing comprehensive order breakdowns and itemized receipts.

### Agent Commerce Journey
1. **Machine Authentication**: An external autonomous agent supplies an `X-Agent-Key` header, verified in constant time using `hmac.compare_digest`.
2. **Autonomous Querying**: The agent queries `/api/agent-commerce/search` or `/api/agent-commerce/recommend` with structured constraints.
3. **Programmatic Order Assembly**: The agent submits an order payload to `/api/agent-commerce/orders`. The backend validates inventory and calculates authoritative line totals.
4. **Checkout Session Generation**: The agent calls `/api/agent-commerce/checkout` to generate a secure payment link for authorized human settlement.

---

## 3. Key Features

- **Conversational Natural-Language Shopping**: Classifies user queries into discrete shopping intents, extracts budget ceilings, and matches target product categories and attributes.
- **Multi-Factor Scored Recommendations**: Ranks catalog items using a composite scoring algorithm incorporating semantic relevance, budget proximity, inventory status, and user ratings.
- **AI Growth Engine (Upsell & Cross-Sell)**: Generates context-aware product upgrades and companion accessories with inventory checks and explainability strings.
- **Server-Authoritative Cart Management**: User-scoped persistent shopping carts with server-calculated subtotals, taxes, and discounts, preventing client-side price tampering.
- **Transactional Inventory Validation**: Validates available stock before cart addition and order placement, performing atomic stock decrements upon payment verification.
- **Resilient Order Lifecycle**: Finite state machine governing orders across `pending_payment`, `paid`, `payment_failed`, and `cancelled` states.
- **Razorpay Payment Integration (Test Mode)**: Supports INR order creation in paise, client-side modal checkout, HMAC-SHA256 signature verification, and idempotent webhook handling.
- **Argon2id Password Security**: Modern, memory-hard password hashing via `argon2-cffi` resistant to GPU-accelerated brute-force attacks.
- **Stateless JWT Authentication**: PyJWT issuance and validation (`HS256`) carrying subject, email, role, and expiration claims.
- **Role-Based Access Control (RBAC)**: Strict permission boundaries for `customer`, `merchant`, and `admin` roles, with privilege escalation prevention on user registration.
- **Agent-to-Agent (A2A) Commerce Protocol**: Dedicated machine-to-machine interface protected by constant-time `X-Agent-Key` verification under an untrusted-client security model.
- **Centralized Security Guardrails**: Input validation bounds, Pydantic v2 schemas, `slowapi` rate limiting on sensitive routes, and request payload size enforcement.
- **Immutable Observable Audit Trail**: Structured event logging in PostgreSQL (`AuditLog` table) tracking authentication, cart modifications, order transitions, payments, and agent requests.
- **Sensitive Data Redaction**: Automatic scrubbing of passwords, JWT secrets, database connection strings, Razorpay keys, and agent secrets from logs and error responses.
- **Merchant Analytics Dashboard**: Real-time business metrics including Gross Merchandise Value (GMV), Average Order Value (AOV), conversion rates, and AI-attributed revenue.
- **Responsive Next.js 16 Storefront**: Server-side rendered and client-hydrated UI featuring an AI Shopping Assistant with 3 operating modes, a live cart drawer, Razorpay modal integration, and customer order history.
- **Production-Ready Containerization**: Multi-stage Docker builds running as unprivileged non-root users (`appuser` and `nextjs`) orchestrated via Docker Compose.
- **Automated Quality Assurance**: 391 backend pytest tests, 94 frontend tsx tests, and 108 Newman API assertions integrated into a GitHub Actions CI pipeline.

---

## 4. Architecture

### System Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                                  CLIENT LAYER                                     |
|                                                                                   |
|   +---------------------------------------+   +-------------------------------+   |
|   |          Web Browser UI               |   |   External Autonomous Agent   |   |
|   |  Next.js 16 (App Router) + React 19   |   |     Machine-to-Machine REST   |   |
|   |       Tailwind CSS v4 Storefront      |   |        (A2A Commerce)         |   |
|   +---------------------------------------+   +-------------------------------+   |
+-----------------------|---------------------------------------|-------------------+
                        | HTTP (JSON / Bearer Token)            | HTTP (X-Agent-Key)
                        v                                       v
+-----------------------------------------------------------------------------------+
|                             GATEWAY & SECURITY BOUNDARY                           |
|                                                                                   |
|   +---------------------------------------------------------------------------+   |
|   | Security Headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options)     |   |
|   | Request Body Size Limiter (MAX_REQUEST_BODY_BYTES = 1MB / 2MB)            |   |
|   | Slowapi Rate Limiter (Sliding Window: Auth 5/min, Search 30/min)          |   |
|   | Constant-Time Agent Key Validator (hmac.compare_digest)                   |   |
|   | JWT Bearer Token Authenticator (PyJWT HS256) & RBAC Authorization         |   |
|   +---------------------------------------------------------------------------+   |
+---------------------------------------|-------------------------------------------+
                                        v
+-----------------------------------------------------------------------------------+
|                                APPLICATION SERVICES                               |
|                                                                                   |
|   +-------------------+  +-------------------+  +-----------------------------+   |
|   |  AI Intent & NLP  |  |  Multi-Factor     |  |       AI Growth Engine      |   |
|   |  Search Service   |  |  Recommendation   |  |   (Upsell & Cross-Sell)     |   |
|   +-------------------+  +-------------------+  +-----------------------------+   |
|   +-------------------+  +-------------------+  +-----------------------------+   |
|   |   Cart & Stock    |  |  Order Lifecycle  |  |   Razorpay Payment Service  |   |
|   |    Management     |  |   State Machine   |  |  (Test Mode & Webhooks)     |   |
|   +-------------------+  +-------------------+  +-----------------------------+   |
|   +-------------------+  +-------------------+  +-----------------------------+   |
|   |  Agent-to-Agent   |  |  Merchant Admin   |  |   Centralized Audit Trail   |   |
|   | Commerce Service  |  | Analytics Engine  |  |     & Redaction Filter      |   |
|   +-------------------+  +-------------------+  +-----------------------------+   |
+---------------------------------------|-------------------------------------------+
                                        v
+-----------------------------------------------------------------------------------+
|                                 PERSISTENCE LAYER                                 |
|                                                                                   |
|   PostgreSQL Database (Supabase) via SQLAlchemy 2.0 ORM Engine                    |
|   Tables: users | products | carts | cart_items | orders | order_items | audit_logs|
+---------------------------------------|-------------------------------------------+
                                        v
+-----------------------------------------------------------------------------------+
|                                EXTERNAL PLATFORMS                                 |
|                                                                                   |
|   Razorpay Payment Gateway (Test Mode)                                            |
|   - Order Creation API                                                            |
|   - Client-Side Checkout JS Modal                                                 |
|   - HMAC-SHA256 Webhook Verification & Auto-Settlement                            |
+-----------------------------------------------------------------------------------+
```

---

## 5. Technology Stack

| Layer | Technology | Version / Spec | Purpose & Rationale |
|---|---|---|---|
| **Backend Framework** | FastAPI | 0.115+ (Python 3.12) | High-performance asynchronous REST API framework with native OpenAPI docs and Pydantic validation |
| **ASGI Server** | Uvicorn | 0.30+ | Production-grade asynchronous ASGI web server supporting worker process clustering |
| **Database** | PostgreSQL | 15+ (Hosted on Supabase) | Enterprise relational persistence offering strict foreign keys, ACID transactions, and JSONB support |
| **ORM** | SQLAlchemy | 2.0+ | Modern async/sync object-relational mapping, declarative models, and connection pool management |
| **Database Migrations** | Alembic | 1.13+ | Version-controlled schema migrations ensuring deterministic database structure |
| **Password Hashing** | Argon2id (`argon2-cffi`) | 23.1+ | Memory-hard password hashing algorithm resistant to GPU and side-channel attacks |
| **Authentication** | PyJWT | 2.8+ (`HS256`) | Stateless JSON Web Token issuance and verification with role-based claims |
| **Rate Limiting** | Slowapi | 0.1.9+ | In-memory sliding-window rate limiting protecting sensitive auth, search, and checkout routes |
| **Payment Gateway** | Razorpay Python SDK | 1.4+ | Test Mode order creation, HMAC-SHA256 signature verification, and webhook handling |
| **Data Validation** | Pydantic | 2.x | Strict schema validation, type coercion, and input sanitization across all request/response models |
| **Frontend Framework** | Next.js | 16.3.3 (App Router) | React server components, static generation, dynamic hydration, and Turbopack bundler |
| **UI Library** | React | 19.2.8 | Declarative component architecture and client-side reactive state management |
| **Frontend Styling** | Tailwind CSS | 4.x | Utility-first CSS framework providing modern responsive layouts and zero-runtime overhead |
| **Frontend Language** | TypeScript | 5.x | Strict static typing across all frontend components, API clients, and domain interfaces |
| **Backend Testing** | Pytest & pytest-asyncio | 8.x | Comprehensive unit, integration, and security regression testing (391 tests) |
| **Frontend Testing** | Node.js Test Runner (`tsx --test`) | Built-in / TSX | Fast, zero-dependency unit and component test runner (94 tests) |
| **API Testing** | Postman / Newman | 6.x | Collection-based API verification suite (35 requests, 108 assertions) |
| **Containerization** | Docker & Docker Compose | Multi-stage Alpine/Slim | Lightweight container images running under unprivileged non-root users (`appuser`, `nextjs`) |
| **Continuous Integration** | GitHub Actions | Ubuntu Latest | Automated testing, credential scanning, and production build pipelines on push and pull requests |

---

## 6. AI Commerce Flow

The platform provides three distinct shopping modes within the unified AI Shopping Assistant:

```
                                  Shopper Query Input
                                           |
                   +-----------------------+-----------------------+
                   |                                               |
                   v                                               v
          "Smart Search" Mode                            "Top AI Picks" Mode
       (POST /api/agent/search)                       (POST /api/agent/recommend)
                   |                                               |
        Intent Classification                          Multi-Factor Scoring Engine
    - Detect Category & Attributes                 - Semantic Relevance (0.35)
    - Extract Budget Ceiling                       - Budget Proximity (0.25)
    - Query Catalog via Database Filters           - Stock Availability (0.20)
                   |                               - Review Rating (0.20)
                   v                                               |
       Filtered Product Listings                                   v
                   |                                  Ranked Scored Products
                   |                                  + Transparent Rationale Tags
                   +-----------------------+-----------------------+
                                           |
                                           v
                             "Upgrades & Accessories" Mode
                               (POST /api/agent/growth)
                                           |
                            +--------------+--------------+
                            |                             |
                            v                             v
                      Upsell Engine                Cross-Sell Engine
                  - Same Category               - Companion Category Affinities
                  - Superior Specs              - High Association Probability
                  - Price Premium (10-35%)      - Active Stock Verification
                  - Active Stock Verification   - Transparent Rationale Tags
                  - Transparent Rationale Tags
                                           |
                                           v
                              Authenticated Add to Cart
                               (POST /api/cart/items)
                                           |
                              Order Creation & Checkout
                                 (POST /api/orders)
                                           |
                             Razorpay Test Mode Payment
                                           |
                              Order Status: Paid & Receipt
```

1. **Smart Search Mode**:
   - The user inputs conversational requirements (e.g., "Mechanical keyboard under 5000 with RGB").
   - The backend intent classifier identifies the action intent (`search`), the target category (`Keyboards`), budget limit (`₹5,000`), and attributes (`RGB`, `Mechanical`).
   - Catalog items are queried, filtered, and returned matching the extracted parameters.

2. **Top AI Picks Mode**:
   - Evaluates matching catalog products against the multi-factor scoring function.
   - Computes normalized scores across relevance, budget fit, inventory availability, and customer satisfaction.
   - Emits explainable rationale strings displayed directly on each recommendation card.

3. **Upgrades & Accessories Mode**:
   - Contextualizes recommendations around a primary selected product.
   - Evaluates higher-tier alternatives within the category (upsell) and companion hardware (cross-sell).
   - Enforces inventory checks to ensure all suggested products are actively in stock.

---

## 7. Recommendation Engine

The recommendation engine (`POST /api/agent/recommend`) ranks candidate products using a deterministic multi-factor scoring algorithm, eliminating non-deterministic hallucinations while ensuring consistent, explainable results.

### Scoring Function
```
Final Score = (0.35 * RelevanceScore) + (0.25 * BudgetFitScore) + (0.20 * AvailabilityScore) + (0.20 * RatingScore)
```

### Component Weights & Definitions
- **Relevance Score (Weight: 0.35)**: Evaluates lexical and token overlap between the user query and the product's title, description, category, and feature specifications.
- **Budget Fit Score (Weight: 0.25)**: Evaluates price proximity relative to the user's budget ceiling:
  - If `price <= budget`: Score is `1.0 - (0.15 * ((budget - price) / budget))`. Products closer to the budget ceiling without exceeding it receive optimal placement.
  - If `price > budget`: Products exceeding budget by up to 15% receive a steep penalty (`0.5 * (1.0 - ((price - budget) / (budget * 0.15)))`). Products exceeding 15% overage score `0.0` and are pruned.
- **Availability Score (Weight: 0.20)**: Real-time inventory status derived from `Product.stock_quantity`:
  - `stock_quantity > 10`: Score = `1.0` (Optimal stock).
  - `0 < stock_quantity <= 10`: Score = `0.7` (Low stock warning).
  - `stock_quantity == 0`: Score = `0.0` (Out of stock; excluded from active recommendations).
- **Rating Score (Weight: 0.20)**: Customer satisfaction rating normalized to a unit scale:
  - `RatingScore = Product.rating / 5.0`.

### Explainability Rationale
Each recommended product includes a human-readable `rationale` field explaining why it was selected. Examples:
- *"Top match for your budget under ₹90,000 with 16GB RAM and exceptional customer satisfaction (4.7/5)."*
- *"Best value option: 12% below budget with in-stock availability and solid 4.4/5 rating."*

---

## 8. Growth Engine

The AI Growth Engine (`POST /api/agent/growth`) analyzes product relationships to generate contextual upsell and cross-sell suggestions aimed at increasing Average Order Value (AOV).

### Upsell Logic
- **Objective**: Recommend a superior product within the same category that provides higher value or performance.
- **Selection Criteria**:
  1. Must share the identical category as the reference product.
  2. Price must fall within a bounded price elevation bracket (typically 10% to 35% higher than the reference price).
  3. Must possess superior technical specifications (e.g., higher RAM, larger battery, superior processor).
  4. Must be actively in stock (`stock_quantity > 0`).
- **Rationale Output**: *"Upgrade option: Higher-tier model offering upgraded processor and expanded 1TB storage for 18% additional investment."*

### Cross-Sell Logic
- **Objective**: Recommend complementary products from companion categories that enhance the utility of the primary purchase.
- **Selection Criteria**:
  1. Category affinity mapping based on established consumer purchasing pairs:
     - `Laptops` -> `Laptop Sleeves`, `Wireless Mice`, `USB-C Hubs`, `Extended Warranty`
     - `Smartphones` -> `Protective Cases`, `Tempered Glass`, `Wireless Chargers`
     - `Cameras` -> `Camera Bags`, `SD Cards`, `Tripods`
  2. Price of companion product is bounded to prevent disproportionate recommendations (typically `<= 40%` of primary product price).
  3. Must be actively in stock (`stock_quantity > 0`).
- **Rationale Output**: *"Recommended companion: Ergonomic wireless mouse designed for seamless compatibility with your laptop."*

### Inventory Guardrails
Products with zero stock are automatically excluded from all growth engine output. If no valid upsell or cross-sell products meet the criteria, the engine safely returns empty arrays rather than suggesting out-of-stock or irrelevant items.

---

## 9. Cart and Order Management

The platform implements a server-authoritative cart and order architecture. Client applications cannot specify unit prices, subtotals, or taxes; all calculations are executed on the backend against verified database records.

### Cart Architecture
- Carts are persisted in the `Cart` table and linked to authenticated customer accounts (`user_id`).
- Items are stored in the `CartItem` table referencing the product ID, quantity, and authoritative unit price.
- Updating cart items validates requested quantities against real-time `Product.stock_quantity`. If a user requests more units than are available in stock, the API rejects the request with `400 Bad Request`.

### Order Lifecycle State Machine

```
   +-------------------------------------------------------------+
   |                       CART CHECKOUT                         |
   +-------------------------------------------------------------+
                                  |
                                  v
                       [ Status: pending_payment ]
                     - Order record created
                     - Stock availability verified
                     - Authoritative total calculated
                                  |
            +---------------------+---------------------+
            |                                           |
            v                                           v
[ Razorpay Payment Authorized ]             [ Payment Failed / Dismissed ]
            |                                           |
            v                                           v
     [ Status: paid ]                         [ Status: payment_failed ]
  - Signature cryptographically verified    - Stock remains untouched
  - Stock atomically decremented            - Order marked failed
  - Active cart cleared                     - User prompted to retry
            |
            v (Admin / User Cancellation)
  [ Status: cancelled ]
  - Inventory restocked
```

### Receipts and Audit Records
Each completed order generates a structured, immutable receipt accessible via `GET /api/orders/{id}`:
- Unique Order Reference UUID
- ISO-8601 Creation and Settlement Timestamps
- Customer Details (ID, Email)
- Itemized Line Items: Product SKU, Title, Quantity, Unit Price, Line Subtotal
- Server-Calculated Subtotal, Tax, Shipping, and Authoritative Total Amount
- Payment Transaction Identifier (Razorpay Payment ID)
- Current Order Status

---

## 10. Razorpay Integration

The payment subsystem integrates with Razorpay in Test Mode, enabling full end-to-end payment simulation without moving real funds.

### Currency and Smallest Unit Handling
- Base Currency: Indian Rupee (`INR`).
- Smallest Unit Conversion: Razorpay requires all transaction amounts to be represented in paise (`₹1.00 = 100 paise`).
- Integer Precision: The backend converts currency values using integer arithmetic (`int(round(amount * 100))`) to eliminate floating-point precision errors.

### Payment Flow
1. **Order Creation (`POST /api/payments/create-order`)**:
   - The backend validates the internal order and calls the Razorpay API:
     ```python
     razorpay_client.order.create({
         "amount": amount_in_paise,
         "currency": "INR",
         "receipt": str(internal_order_id),
         "notes": {"internal_order_id": str(internal_order_id)}
     })
     ```
   - The backend returns the `razorpay_order_id`, `amount`, and public `key_id`.
2. **Client Modal Execution**:
   - The frontend dynamically loads `https://checkout.razorpay.com/v1/checkout.js`.
   - Opens the payment modal with the order parameters.
   - The user selects a test payment instrument (Test Netbanking, Test Cards, or Test UPI).
3. **Signature Verification (`POST /api/payments/verify`)**:
   - Upon completion, the client receives `razorpay_payment_id`, `razorpay_order_id`, and `razorpay_signature`.
   - The backend verifies the cryptographic signature using HMAC-SHA256:
     ```python
     razorpay_client.utility.verify_payment_signature({
         "razorpay_order_id": payload.razorpay_order_id,
         "razorpay_payment_id": payload.razorpay_payment_id,
         "razorpay_signature": payload.razorpay_signature
     })
     ```
   - If verification succeeds, the order status transitions to `paid`, stock is decremented, and the cart is emptied.
4. **Webhook Auto-Settlement (`POST /api/payments/webhook`)**:
   - Asynchronous payment confirmations sent by Razorpay are verified against `X-Razorpay-Signature` using `RAZORPAY_WEBHOOK_SECRET`.
   - Idempotency is enforced: Webhook processing checks the `AuditLog` table for the `payment_id`. Repeated webhook deliveries are safely acknowledged with `200 OK` without duplicate processing.

---

## 11. Authentication and Authorization

The platform enforces strict authentication and role-based access control across all operational endpoints.

### Password Security: Argon2id
- User passwords are encrypted using the Argon2id algorithm via `argon2-cffi`.
- Argon2id provides memory-hardness and time-hardness parameters designed to defeat GPU-accelerated hash cracking.
- Raw passwords and hash salts are never logged or exposed in API responses.

### Token Specification: PyJWT (HS256)
- **Algorithm**: HMAC with SHA-256 (`HS256`).
- **Payload Schema**:
  ```json
  {
    "sub": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "email": "customer@example.com",
    "role": "customer",
    "iat": 1725450000,
    "exp": 1725453600
  }
  ```
- **Expiration**: Configurable via `JWT_EXPIRATION_MINUTES` (default: 60 minutes).
- **Revocation & Expiry Handling**: Expired tokens return `401 Unauthorized`. The frontend automatically clears expired tokens from storage.

### Role Hierarchy & Access Matrix
- **`customer`**:
  - Allowed: Browse catalog, execute AI searches, view recommendations, manage personal cart, checkout, view personal order history.
  - Denied: Catalog modification, merchant dashboard, administrative logs, role changes.
- **`merchant`**:
  - Allowed: All customer privileges plus product creation, product editing, stock adjustments, and access to merchant revenue analytics.
  - Denied: Administrative user management, system-wide configuration.
- **`admin`**:
  - Allowed: Full platform access, audit log inspection, user role assignment, system health monitoring.

### Privilege Escalation Prevention
The public customer registration endpoint (`POST /api/auth/register`) strictly sets the newly created user's role to `customer`, unconditionally ignoring any `role` attribute passed in the request body. Elevated roles (`merchant`, `admin`) can only be granted by database seeding or dedicated administrative endpoints.

---

## 12. Agent-to-Agent Commerce

The Agent-to-Agent (A2A) Commerce interface enables external autonomous software agents to discover products, request recommendations, assemble orders, and initialize checkout sessions programmatically.

### Security Boundary: `X-Agent-Key`
- External agents authenticate by supplying an `X-Agent-Key` HTTP header.
- Verification uses Python's constant-time comparison:
  ```python
  import hmac
  is_valid = hmac.compare_digest(provided_key, settings.COMMERCE_AGENT_KEY)
  ```
- Constant-time validation prevents timing side-channel attacks aimed at discovering key values.

### Untrusted Client Principle
All requests from external agents are treated as untrusted inputs:
- Agent-supplied prices, subtotals, or discount rates are ignored.
- Inventory is verified against database stock levels at the moment of request.
- Agents cannot mark orders as paid or bypass payment verification.

### Machine-Readable Endpoints
- `POST /api/agent-commerce/search`: Autonomous product discovery supporting category, price, and attribute constraints.
- `POST /api/agent-commerce/recommend`: Contextual recommendations formatted specifically for agent decision models.
- `POST /api/agent-commerce/orders`: Programmatic cart creation and order assembly.
- `POST /api/agent-commerce/checkout`: Checkout session generation returning a secure hosted payment URL for authorized settlement.

---

## 13. API Reference

### Authentication Endpoints
| Method | Endpoint | Description | Authentication | Role |
|---|---|---|---|---|
| `POST` | `/api/auth/register` | Register new customer account | None (Public) | Any |
| `POST` | `/api/auth/login` | Authenticate user & return JWT | None (Public) | Any |
| `GET` | `/api/auth/me` | Retrieve profile of authenticated user | Bearer JWT | Any |

### Product Catalog Endpoints
| Method | Endpoint | Description | Authentication | Role |
|---|---|---|---|---|
| `GET` | `/api/products` | List catalog products with filtering | None (Public) | Any |
| `GET` | `/api/products/{id}` | Retrieve individual product details | None (Public) | Any |
| `POST` | `/api/products` | Create a new catalog product | Bearer JWT | `merchant`, `admin` |
| `PUT` | `/api/products/{id}` | Update product details or stock | Bearer JWT | `merchant`, `admin` |
| `DELETE` | `/api/products/{id}` | Remove product from catalog | Bearer JWT | `merchant`, `admin` |

### AI Shopping & Assistant Endpoints
| Method | Endpoint | Description | Authentication | Role |
|---|---|---|---|---|
| `POST` | `/api/agent/search` | Natural language catalog search | None (Public) | Any |
| `POST` | `/api/agent/recommend` | Scored multi-factor recommendations | None / Optional JWT | Any |
| `POST` | `/api/agent/growth` | Contextual upsell and cross-sell suggestions | None / Optional JWT | Any |

### Cart Management Endpoints
| Method | Endpoint | Description | Authentication | Role |
|---|---|---|---|---|
| `GET` | `/api/cart` | View authenticated user's active cart | Bearer JWT | `customer` |
| `POST` | `/api/cart/items` | Add product to cart with stock validation | Bearer JWT | `customer` |
| `PUT` | `/api/cart/items/{item_id}` | Update quantity of item in cart | Bearer JWT | `customer` |
| `DELETE` | `/api/cart/items/{item_id}` | Remove specific item from cart | Bearer JWT | `customer` |
| `DELETE` | `/api/cart` | Empty entire active cart | Bearer JWT | `customer` |

### Order & Payment Endpoints
| Method | Endpoint | Description | Authentication | Role |
|---|---|---|---|---|
| `POST` | `/api/orders` | Create order from active cart | Bearer JWT | `customer` |
| `GET` | `/api/orders` | Retrieve authenticated order history | Bearer JWT | `customer` |
| `GET` | `/api/orders/{id}` | Retrieve order receipt details | Bearer JWT | `customer`, `admin` |
| `POST` | `/api/payments/create-order` | Initialize Razorpay payment order | Bearer JWT | `customer` |
| `POST` | `/api/payments/verify` | Verify client payment signature | Bearer JWT | `customer` |
| `POST` | `/api/payments/webhook` | Razorpay webhook notification handler | `X-Razorpay-Signature` | Service |

### Agent-to-Agent (A2A) Endpoints
| Method | Endpoint | Description | Authentication | Role |
|---|---|---|---|---|
| `POST` | `/api/agent-commerce/search` | Machine product discovery | `X-Agent-Key` | Agent |
| `POST` | `/api/agent-commerce/recommend` | Machine-tailored recommendations | `X-Agent-Key` | Agent |
| `POST` | `/api/agent-commerce/orders` | Programmatic order creation | `X-Agent-Key` | Agent |
| `POST` | `/api/agent-commerce/checkout` | Agent checkout link generation | `X-Agent-Key` | Agent |

### Merchant Dashboard & Analytics Endpoints
| Method | Endpoint | Description | Authentication | Role |
|---|---|---|---|---|
| `GET` | `/api/dashboard/metrics` | Key metrics: GMV, AOV, conversions | Bearer JWT | `merchant`, `admin` |
| `GET` | `/api/dashboard/revenue` | Revenue time-series analytics | Bearer JWT | `merchant`, `admin` |
| `GET` | `/api/dashboard/ai-attribution` | AI-driven revenue attribution stats | Bearer JWT | `merchant`, `admin` |

### Health & Monitoring Endpoints
| Method | Endpoint | Description | Authentication | Role |
|---|---|---|---|---|
| `GET` | `/health` | System and database health status | None (Public) | Any |
| `GET` | `/metrics` | Operational performance metrics | Bearer JWT | `admin` |

---

## 14. Security and Guardrails

The platform implements multi-layer defense-in-depth across the network, application, and database layers:

- **Centralized Input Validation**: All payloads are validated using Pydantic v2 schemas. String inputs are length-bounded, whitespace-normalized, and checked for control characters.
- **In-Memory Rate Limiting**: Built on `slowapi`, enforcing sliding-window rate limits:
  - Authentication routes: `5 requests / minute` per IP.
  - Payment verification: `10 requests / minute` per IP.
  - AI Search and Recommendation routes: `30 requests / minute` per IP.
  - Excessive requests receive standard `429 Too Many Requests` responses with `Retry-After` headers.
- **Request Body Size Limits**: Custom ASGI middleware inspects incoming `Content-Length` headers. Payloads exceeding `MAX_REQUEST_BODY_BYTES` (default: 1MB or 2MB in production) are rejected with `413 Payload Too Large`.
- **Defensive HTTP Security Headers**: Configured across all HTTP responses:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: geolocation=(), camera=(), microphone=()`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (enforced in production)
- **Sensitive Data Redaction Filter**: A centralized logging filter (`SensitiveDataRedactionFilter`) automatically sanitizes strings matching sensitive patterns (passwords, JWT secrets, database connection URLs, Razorpay keys, and agent keys) before emission to stdout, stderr, or log sinks.

---

## 15. Audit Trail and Observability

The platform maintains an append-only, relational audit trail stored in the `AuditLog` table.

### Relational Schema
- `id`: UUID primary key.
- `event_type`: Standardized event classification:
  - `USER_REGISTER`, `USER_LOGIN`
  - `CART_ITEM_ADDED`, `CART_ITEM_REMOVED`, `CART_CLEARED`
  - `ORDER_CREATED`, `ORDER_STATUS_CHANGED`
  - `PAYMENT_ATTEMPTED`, `PAYMENT_SUCCESS`, `PAYMENT_FAILED`
  - `AGENT_REQUEST`, `RECOMMENDATION_GENERATED`
- `user_id`: Optional UUID referencing the user account.
- `resource_type`: Identifier of affected entity (`order`, `cart`, `product`, `user`).
- `resource_id`: Primary key of the affected entity.
- `details`: JSONB object containing sanitized contextual metadata.
- `ip_address`: Originating client IP address.
- `created_at`: ISO-8601 UTC timestamp.

### Immutability & Forensics
The audit log table is append-only; no UPDATE or DELETE routes are exposed. This log provides forensic auditability for financial reconciliation, dispute resolution, rate limit monitoring, and security incident investigations.

---

## 16. Merchant Dashboard

The Merchant Dashboard (`/api/dashboard/*`) provides store operators with real-time operational and financial visibility:

- **Revenue Metrics**:
  - Gross Merchandise Value (GMV): Total revenue generated across completed transactions.
  - Average Order Value (AOV): Mean revenue per completed order (`Total Revenue / Completed Orders`).
  - Cart-to-Order Conversion Rate: Percentage of assembled carts that culminate in verified purchases.
- **Inventory Monitoring**:
  - Identifies active stock levels across all catalog items.
  - Generates low-stock alerts (`stock_quantity <= 10`) and out-of-stock notices (`stock_quantity == 0`).
- **AI Revenue Attribution**:
  - Measures the proportion of total store revenue originating from AI Shopping Assistant interactions:
    - Smart Search conversions
    - Top AI Picks recommendations
    - Growth Engine upsell and cross-sell selections
  - Tracks uplift in Average Order Value directly attributable to growth recommendations.

---

## 17. Frontend Experience

The frontend is implemented as a modern single-page application built on Next.js 16 (App Router), React 19, TypeScript 5, and Tailwind CSS v4.

### Storefront Components & Layout
- **Catalog Navigation**: Grid layout displaying products with high-resolution imagery, pricing, stock indicators, and customer review star ratings.
- **AI Shopping Assistant**:
  - Positioned prominently at the top of the storefront.
  - Provides a three-way mode toggle:
    - `Smart Search`: Conversational natural-language search with extracted constraint tags.
    - `Top AI Picks`: Scored recommendation cards displaying composite match percentages and explainability rationale tags.
    - `Upgrades & Accessories`: Contextual growth engine interface surfacing upsell upgrades and companion add-ons.
- **Slide-Out Cart Drawer**:
  - Slide-out panel accessible from any page view.
  - Displays live item counts, item-level quantity controls, subtotal, shipping cost, tax calculation, and checkout trigger.
- **Razorpay Modal Integration**:
  - Seamlessly initializes Razorpay Checkout JS modal.
  - Handles payment completion, authorization callbacks, error messages, and automatic cart clearing.
- **Customer Order History**:
  - Dedicated order history view accessible to authenticated customers.
  - Renders past orders with status badges (`Pending Payment`, `Paid`, `Cancelled`), timestamps, and total amounts.
  - View Receipt modal renders complete order receipts with line-item breakdowns, unit prices, and quantities.

---

## 18. Testing

The platform maintains comprehensive test coverage across both backend and frontend codebases.

### Backend Test Suite
- **Framework**: Pytest with `pytest-asyncio` and `httpx`.
- **Test Count**: **391 passing tests** across 30 test files.
- **Execution Time**: ~44 seconds in isolated test mode.
- **Coverage Areas**:
  - Authentication: Argon2id hashing, registration, login, token claims, token expiration.
  - Role-Based Access Control: Permission checks, privilege escalation prevention.
  - Product Catalog: CRUD operations, search filters, pagination.
  - AI Intent & Search: Intent parsing, budget extraction, category matching.
  - Recommendation Engine: Multi-factor scoring calculations, weight balances, rationale generation.
  - Growth Engine: Upsell price bounds, cross-sell category affinities, inventory suppression.
  - Cart & Orders: Inventory validation, authoritative pricing, state machine transitions.
  - Razorpay Integration: Order creation, HMAC-SHA256 signature verification, webhook processing, idempotency.
  - Agent-to-Agent Commerce: Constant-time key verification, untrusted client model enforcement.
  - Security & Hardening: Rate limiting, payload size limits, security headers, credential redaction.

### Frontend Test Suite
- **Framework**: Node.js Test Runner with `tsx` (`tsx --test`).
- **Test Count**: **94 passing tests** across 11 test suites.
- **Execution Time**: ~550 milliseconds.
- **Coverage Areas**:
  - API Client Layer: Endpoint bindings, query formatting, response error handling.
  - Authentication Helpers: Token storage in `localStorage`, expiration detection, auth header injection.
  - AI Assistant UI: Mode toggling between Smart Search, Top AI Picks, and Growth Engine.
  - Recommendation UI: Scored product rendering, match percentage badges, rationale tags, Add-to-Cart flows.
  - Growth Engine UI: Upsell cards, Cross-sell companion cards, Add-to-Cart synchronization.
  - Cart Drawer: Item quantity increment/decrement, item removal, price calculation.
  - Order History & Receipt UI: Order listing, status badges, receipt modal breakdown.

### Postman / Newman API Collection
- **File**: `docs/postman/AI-Commerce-Agent-API.postman_collection.json`.
- **Test Count**: **35 API requests** and **108 automated assertions** validating end-to-end integration contracts across all public and protected routes.

---

## 19. CI/CD Pipeline

Continuous integration is automated via GitHub Actions defined in `.github/workflows/ci.yml`.

### Workflow Triggers
- Pushes to the `main` branch.
- Pull Requests targeting the `main` branch.
- Manual execution via `workflow_dispatch`.

### Pipeline Jobs
1. **`backend-tests` (Python 3.12)**:
   - Sets up Python 3.12 environment with pip caching.
   - Spins up a dedicated PostgreSQL service container.
   - Installs locked backend dependencies via `pip install -r backend/requirements.txt`.
   - Executes the complete backend test suite: `pytest backend/tests/ -v`.
   - Executes automated secret leak detection tests verifying zero committed credentials.
2. **`frontend-build` (Node.js 20)**:
   - Sets up Node.js 20 environment with npm caching.
   - Installs locked dependencies via clean `npm ci`.
   - Executes the frontend test suite: `npm test`.
   - Executes the production Next.js build: `npm run build` (with telemetry disabled and TypeScript checking enabled).

### Pipeline Security & Failure Safety
- CI operates under `permissions: contents: read` according to the principle of least privilege.
- No production secrets or API keys are configured in CI; tests use isolated development defaults.
- Commands run with `-eo pipefail` to ensure any failing step terminates the pipeline immediately.

---

## 20. Docker and Production Readiness

The application is containerized using multi-stage, production-hardened Dockerfiles.

### Backend Container (`backend/Dockerfile`)
- Base image: `python:3.12-slim`.
- Multi-stage build minimizes final image size by discarding build tools and intermediate artifacts.
- Dependencies installed using `--no-cache-dir`.
- Runs as an unprivileged, dedicated non-root user: `appuser` (UID 10001).
- Exposes port 8000.

### Frontend Container (`frontend/Dockerfile`)
- Base image: `node:20-alpine`.
- Multi-stage build structure:
  1. `deps`: Installs packages via `npm ci`.
  2. `builder`: Compiles Next.js standalone output via `npm run build`.
  3. `runner`: Minimal Alpine runtime copying only necessary standalone server files.
- Runs as an unprivileged, dedicated non-root user: `nextjs` (UID 1001).
- Exposes port 3000.

### Multi-Container Orchestration (`docker-compose.yml`)
- Orchestrates `backend` and `frontend` services with bridge network isolation.
- Configures health check probes (`/health` endpoint on backend).
- Configures restart policies (`restart: unless-stopped`).
- Maps host ports 8000 (FastAPI) and 3000 (Next.js).

---

## 21. Environment Configuration

The application separates configuration from code using environment variables. All variables are documented in `.env.example` templates. Never commit real credentials to version control.

### Backend Environment Variables (`backend/.env.example`)
| Variable | Description | Example / Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/dbname` |
| `JWT_SECRET` | Cryptographic secret for signing JWTs | High-entropy random string (32+ chars) |
| `JWT_ALGORITHM` | Algorithm used for JWT signing | `HS256` |
| `JWT_EXPIRATION_MINUTES`| Access token lifetime in minutes | `60` |
| `COMMERCE_AGENT_KEY` | Shared secret key for Agent-to-Agent API | High-entropy random string |
| `RAZORPAY_KEY_ID` | Razorpay public key identifier | `rzp_test_...` |
| `RAZORPAY_KEY_SECRET` | Razorpay private secret key | Secret string |
| `RAZORPAY_WEBHOOK_SECRET`| Secret used to sign Razorpay webhooks | Secret string |
| `ENVIRONMENT` | Application execution environment | `development` / `test` / `production` |
| `ALLOWED_ORIGINS` | Comma-separated CORS allowed origins | `http://localhost:3000,http://127.0.0.1:3000` |
| `MAX_REQUEST_BODY_BYTES`| Maximum permitted HTTP request body size | `1048576` (1MB) |

### Frontend Environment Variables (`frontend/.env.example`)
| Variable | Description | Example / Default |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Base URL of the backend FastAPI service | `http://localhost:8000` |
| `NEXT_PUBLIC_RAZORPAY_KEY_ID` | Public Razorpay key ID for checkout modal | `rzp_test_...` |

---

## 22. Local Development Setup

### Prerequisites
- Python 3.12 or newer
- Node.js 20 LTS or newer (with npm)
- PostgreSQL 15+ (or Supabase instance)
- Docker & Docker Compose (optional, for containerized execution)

### Backend Setup
1. Navigate to the backend directory and create a virtual environment:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your local PostgreSQL credentials and test keys
   ```
4. Run database migrations:
   ```bash
   alembic upgrade head
   ```
5. Start the development server:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   The API will be available at `http://127.0.0.1:8000` and interactive docs at `http://127.0.0.1:8000/docs`.

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node.js dependencies:
   ```bash
   npm install
   ```
3. Configure environment variables:
   ```bash
   cp .env.example .env.local
   # Set NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
4. Start the Next.js development server:
   ```bash
   npm run dev
   ```
   The storefront will be accessible at `http://localhost:3000`.

### Running via Docker Compose
To build and start both the backend and frontend services in isolated containers:
```bash
docker compose up --build
```
To stop the services:
```bash
docker compose down
```

---

## 23. Verification and Quality Gates

Before submitting changes or deploying, execute the following quality gates:

### 1. Backend Verification
```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```
All 391 tests should pass with zero failures.

### 2. Frontend Verification
```bash
cd frontend
npm test
```
All 94 tests across 11 test suites should pass.

### 3. Production Build Verification
```bash
cd frontend
npm run build
```
The Next.js production build and TypeScript compilation should complete with zero errors.

### 4. Git Hygiene & Diff Checks
```bash
git diff --check
git status
```
Verify that the working tree is clean and that no secrets or unintended artifacts are tracked.

---

## 24. Project Development Progress

The project was constructed across 18 sequential engineering phases:

- **Phase 1: Project Scaffolding & Environment Setup**: Repository structure, virtual environments, dependency manifests.
- **Phase 2: Database Schema & Supabase PostgreSQL**: Relational schema, SQLAlchemy 2.0 models, Alembic migrations.
- **Phase 3: Product Catalog & Deterministic Seeding**: Initial product catalog data across laptops, electronics, and accessories.
- **Phase 4: Semantic & Filtered Product Discovery**: Catalog query APIs supporting category, price range, and attribute filtering.
- **Phase 5: AI Agent Intent Extraction**: Intent classification engine parsing queries into structured search parameters.
- **Phase 6: AI Intent to Catalog Search Integration**: Connecting natural-language queries to dynamic database filter generation.
- **Phase 7: Multi-Factor Recommendation Engine**: Implementing weighted scoring (relevance, budget, availability, rating) and rationale generation.
- **Phase 8: AI Growth Engine (Upsell & Cross-Sell)**: Contextual product upgrades and companion category affinities with inventory checks.
- **Phase 9: Cart and Order Management Foundation**: Relational cart models, inventory validation, and authoritative total calculations.
- **Phase 10: Razorpay Payment Integration (Test Mode)**: INR order creation in paise and signature verification.
- **Phase 11: Razorpay Webhooks & Auto-Settlement**: Cryptographic webhook signature verification and idempotent order settlement.
- **Phase 12: Security Guardrails & Input Boundaries**: Centralized input sanitization, rate limiting, and payload size bounds.
- **Phase 13: Observable Audit Trail & Redaction Filter**: Structured `AuditLog` table and secret-free logging filter.
- **Phase 14: Merchant Analytics Dashboard**: GMV, AOV, conversion rate, and AI attribution metrics APIs.
- **Phase 15: Agent-to-Agent (A2A) Commerce Protocol**: Constant-time `X-Agent-Key` verification and machine-to-machine checkout endpoints.
- **Phase 16: Adversarial Security Regression Suite**: 390+ security, boundary, and regression tests verifying platform integrity.
- **Phase 17: User Authentication & Role-Based Access Control**:
  - Phase 17A: Argon2id password hashing foundation and PyJWT token engine.
  - Phase 17B: User registration and login endpoints with privilege escalation defense.
  - Phase 17C: Protected endpoints, ownership verification, and role-based permissions.
- **Phase 18: Full-Stack Storefront & Production Integration**:
  - Phase 18A: Production configuration hardening and environment management.
  - Phase 18B: GitHub Actions CI pipeline with backend testing and secret scanning.
  - Phase 18C: API application hardening, security headers, and rate limiting.
  - Phase 18D: Frontend authentication state and JWT token management.
  - Phase 18E: CI/CD validation and automated pipeline verification.
  - Phase 18F: Multi-stage Docker containerization and Docker Compose orchestration.
  - Phase 18 Step 1: Next.js 16 Storefront Foundation & Catalog UI.
  - Phase 18 Step 2: Customer Authentication & Session Management UI.
  - Phase 18 Step 3: Interactive Cart Drawer & Stock Management UI.
  - Phase 18 Step 4A: Checkout Flow & Order Assembly UI.
  - Phase 18 Step 4B: Razorpay Modal Integration & Payment Verification UI.
  - Phase 18 Step 4C: Customer Order History & Authoritative Receipts UI.
  - Phase 18 Step 5.1: AI Scored Recommendations UI (Smart Search vs Top AI Picks).
  - Phase 18 Step 5.2: AI Growth Engine UI (Upgrades & Accessories Mode).
  - Phase 18 Step 5.3: End-to-End System Verification & Checkpoint.

---

## 25. Current Project Status

- **Status**: Completed through Phase 18 (Frontend Step 5.3).
- **Latest Verified Commit**: `0f3ccd9` (`feat: add AI growth engine UI`).
- **Git Branch**: `main` (clean working tree, synchronized with `origin/main`).
- **Test Results**:
  - Backend: **391 passed** (100% pass rate).
  - Frontend: **94 passed** (100% pass rate).
  - Postman: **35 requests / 108 assertions passed**.
- **Production Build**: Next.js 16 App Router build passes cleanly with zero TypeScript or linting errors.

---

## 26. Limitations and Operational Scope

To maintain technical accuracy, the following operational boundaries are documented:
- **Payment Processing**: Currently operating exclusively in Razorpay Test Mode. Production monetary transactions require merchant onboarding, KYC verification, and live API credentials.
- **Single Merchant Tenancy**: The database schema and merchant dashboard are designed around a single store operator model rather than a multi-vendor marketplace.
- **Deterministic AI Heuristics**: Intent classification and recommendation scoring rely on deterministic natural-language heuristics and weighted scoring rather than paid third-party LLM APIs. This design ensures zero external API latency, zero runtime cost, and zero leakage of customer data to third parties.
- **Human-in-the-Loop Agent Settlement**: The Agent-to-Agent commerce interface generates secure payment sessions and links requiring human authorization; fully autonomous programmatic bank balance settlement is not supported.

---

## 27. Future Improvements

- **Vector Similarity Search**: Integrating vector database capabilities (such as `pgvector`) for dense embedding retrieval alongside lexical keyword search.
- **Multi-Vendor Marketplace Support**: Extending database schemas to support multiple independent vendors with automated payout splitting via Razorpay Route.
- **Pluggable LLM Adapter Layer**: Adding optional sidecar connectors for external large language models (e.g., OpenAI, Anthropic, or local Ollama models) for open-ended conversational dialogues.
- **Real-Time WebSockets**: Implementing WebSocket feeds for live stock depletion updates and real-time order status tracking.

---

## 28. License

This repository is developed for evaluation, demonstration, and competition purposes under the Razorpay AI Buildathon. All rights reserved. No open-source license is granted at this time.

---

## 29. Author and Repository

- **Author / Developer**: Roushan Kumar (`Roushan0012`)
- **GitHub Repository**: [https://github.com/Roushan0012/AI-Ecommerce-Agent](https://github.com/Roushan0012/AI-Ecommerce-Agent)
- **Track**: Track 01 — AI Commerce Agent (Razorpay AI Buildathon)
