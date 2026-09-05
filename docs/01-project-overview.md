# Project Overview

## 1. Executive Summary

The AI Commerce Agent Platform is a full-stack, authoritative e-commerce system engineered for autonomous commerce operations, conversational catalog discovery, multi-factor recommendation and growth engines, and machine-to-machine transactions. Developed within the scope of Track 01 (AI Commerce Agent) of the Razorpay AI Buildathon, the platform bridges the gap between traditional consumer storefronts and external autonomous buyer agents.

The system is constructed with a FastAPI backend running on Python 3.12, a PostgreSQL relational database hosted on Supabase and managed via SQLAlchemy 2.0 ORM, Razorpay payment processing operating in Test Mode with cryptographic signature and webhook verification, Argon2id password security with role-based JWT authentication, and a modern customer storefront built using Next.js 16 (App Router), React 19, and Tailwind CSS v4.

---

## 2. Problem Statement

### 2.1 Limitations of Conventional E-Commerce Systems
Traditional online commerce platforms rely primarily on rigid keyword indexing, manual categorical hierarchies, and static rule-based merchandising. These mechanisms exhibit several architectural shortcomings:
- Keyword Sensitivity: Minor variations in phrasing, typos, or conversational language (e.g., "looking for something portable to charge my laptop under 3000 rupees") frequently fail or return irrelevant results when matching against strict relational database text queries.
- Disconnected Merchandising: Recommendations are commonly generated using static associations or simple collaborative filtering that ignores real-time stock levels, budget proximity, and technical specification comparisons.
- Manual Basket Construction: Upselling (recommending a superior product in the same class) and cross-selling (recommending complementary accessories) are often hardcoded by store administrators, failing to adapt dynamically to the shopper's active budget constraints and product selections.
- Client-Side Trust Vulnerabilities: Many storefront implementations allow client applications to calculate or submit item prices, discounts, and order totals, exposing the backend to price manipulation and inventory race conditions.

### 2.2 The Autonomous Agent Gap
As autonomous software agents emerge to assist human consumers in product procurement, existing e-commerce systems lack standardized, machine-readable interfaces tailored for programmatic negotiation and transaction execution. Autonomous agents interacting with standard web stores face:
- HTML Scraping Fragility: Parsing visual frontends is brittle, error-prone, and susceptible to layout updates.
- Untrusted Client Security Risks: Storefronts rarely distinguish between human browsers and automated agents, lacking granular authorization boundaries, timing-attack protection, and idempotent order creation protocols.
- Payment Delegation Dilemmas: External agents cannot be granted unrestricted access to customer payment credentials or banking interfaces without introducing severe financial security liabilities.

---

## 3. The Proposed Solution

The platform provides an authoritative, full-stack architecture that addresses these challenges through two coordinated operational surfaces:

1. A Consumer-Facing Intelligent Storefront:
   - Natural-language shopping assistant capable of parsing intent, extracting explicit budget constraints, and matching catalog attributes.
   - Deterministic multi-factor recommendation engine combining keyword relevance, category alignment, budget proximity, and inventory health into explainable rankings.
   - AI growth engine that analyzes product specifications and category affinities to surface viable upsell upgrades and companion cross-sell accessories.
   - Secure slide-out cart drawer, transactional stock reservation, Razorpay modal checkout in Test Mode, and authenticated customer order history.

2. A Dedicated Agent-to-Agent (A2A) Commerce Interface:
   - Protected machine-to-machine REST endpoints authenticated via constant-time API key verification (`X-Agent-Key`).
   - Strict untrusted-client security model where all pricing, totals, and inventory checks remain server-authoritative.
   - Programmatic catalog discovery, stock checking, cart assembly, idempotent order creation, and payment link generation.
   - Payment boundary isolation: External agents can assemble orders and request payment initialization, but cannot mark orders as paid or bypass cryptographic signature verification.

---

## 4. Target Users and Personas

| User Persona | Role | Primary Objectives | Access Level |
|---|---|---|---|
| Consumer / Shopper | `customer` | Search catalog using natural language, receive explainable recommendations, manage persistent shopping cart, complete test payments, and review historical receipts. | Public catalog and agent search; Authenticated cart, checkout, and order history. |
| External Autonomous Agent | Agent (`X-Agent-Key`) | Programmatically discover products, check stock levels, assemble carts, create orders idempotently, and retrieve payment links on behalf of users. | Machine-to-machine endpoints under `/api/agent-commerce/*`. |
| Store Operator / Merchant | `merchant` | Manage catalog inventory, view real-time revenue analytics, monitor cart-to-order conversion rates, and track AI-attributed revenue performance. | Protected merchant endpoints under `/api/products/*` and `/api/dashboard/*`. |
| System Administrator | `admin` | Inspect platform-wide audit logs, monitor database connectivity and service health, manage user accounts, and oversee platform security. | Global administrative access across all endpoints and audit facilities. |

---

## 5. Major Capabilities

### 5.1 Conversational Catalog Discovery
Shoppers can enter unconstrained natural-language requests into the storefront AI Shopping Assistant. The backend intent classification service parses user prompts into structured parameters:
- Intent classification (`product_search`, `general`, `inquiry`)
- Target category detection (`Audio`, `Computer Accessories`, `Chargers & Cables`, `Work & Travel`)
- Minimum and maximum budget limits (e.g., "under 5000", "between 2000 and 4000")
- Specific product attributes (e.g., "mechanical", "ANC", "braided", "GaN")

### 5.2 Deterministic Multi-Factor Recommendations
Rather than relying on non-deterministic external language models that can hallucinate catalog items or invent prices, candidate products are evaluated against a multi-factor scoring algorithm:
- Category alignment (30% weight)
- Text and keyword relevance across title, description, and JSONB attributes (35% weight)
- Price proximity and budget fitness (20% weight)
- Real-time inventory health (15% weight)
Each recommendation produces a composite score from 0.0 to 1.0 alongside an explainable rationale tag justifying the recommendation to the shopper.

### 5.3 Context-Aware Growth Engine
The platform includes an automated growth engine operating across two distinct merchandising disciplines:
- Upsell: Identifies superior products in the same category that cost more than the reference item (up to 4.5x or bounded by the user's budget) and evaluates concrete specification improvements (e.g., higher power output, hybrid ANC, expanded battery capacity, hot-swappable switches).
- Cross-Sell: Uses category affinity pairings to recommend complementary companion products and accessories (e.g., pairing a mechanical keyboard with an ergonomic mouse, extended felt desk mat, or USB-C dock).

### 5.4 Authoritative Cart and Order Management
- Persistent carts backed by PostgreSQL tables (`carts` and `cart_items`), linked to authenticated customer accounts.
- Strict server-side arithmetic: Subtotals, item line totals, discounts, and final balances are computed exclusively on the backend.
- Transactional inventory checks: Attempting to add or increase item quantities beyond available `Product.inventory` is rejected with `400 Bad Request`.
- Explicit order state lifecycle: `pending_payment` -> `paid` (upon cryptographic verification) or `payment_failed` / `cancelled`.

### 5.5 Razorpay Payment Integration (Test Mode)
- Native INR transactions with precision integer conversion to paise (`₹1.00 = 100 paise`).
- Razorpay order creation via the official Python SDK, passing server-authoritative totals and unique receipt identifiers.
- Client-side Razorpay Checkout JS modal integration on the Next.js storefront.
- Cryptographic verification of payment signatures (`razorpay_payment_id`, `razorpay_order_id`, `razorpay_signature`) via HMAC-SHA256.
- Asynchronous webhook processing with replay protection, amount reconciliation, and idempotent order settlement.

### 5.6 Enterprise Security and Auditability
- Argon2id password hashing via `argon2-cffi` with time- and memory-hardness.
- Stateless PyJWT bearer tokens signed with HMAC-SHA256 (`HS256`).
- Privilege escalation prevention: Registration endpoints enforce the `customer` role unconditionally.
- Rate limiting on sensitive authentication, search, and checkout routes via `slowapi`.
- Request body payload size limits (2MB default) blocking oversized input.
- HTTP security headers: Content Security Policy, HSTS, X-Frame-Options, X-Content-Type-Options.
- Relational audit logging in the `audit_logs` table tracking authentication, cart modifications, orders, payments, and agent requests.
- Automatic redaction of sensitive credentials (passwords, JWT secrets, Razorpay keys, agent keys) from all logs and validation error responses.

---

## 6. Buildathon Context (Track 01: AI Commerce Agent)

This project was developed for the Razorpay AI Buildathon under Track 01 (AI Commerce Agent). The track objectives require building an intelligent commerce agent that can assist users with product discovery, provide contextual merchandising, manage the purchasing process, and integrate with Razorpay payment workflows.

Key Buildathon requirements fulfilled by this platform:
- AI-Driven Shopping Assistant: Natural-language query comprehension and intent mapping.
- Contextual Merchandising: Dynamic multi-factor scoring and autonomous upsell/cross-sell generation.
- Full E-Commerce Transaction Lifecycle: Catalog -> Cart -> Order -> Razorpay Checkout -> Webhook Verification -> Order Receipt.
- Agent-to-Agent Protocol: Dedicated machine-readable API enabling external autonomous buyer agents to complete transactions.
- Security and Authoritative Control: Rejection of client-submitted prices, constant-time agent authentication, and tamper-proof webhook verification.

---

## 7. Customer Commerce Journey

The typical customer shopping journey proceeds through the following verified stages:

```
[Customer visits storefront]
        |
        v
[AI Shopping Assistant Query] ---> (Smart Search / Top AI Picks / Upgrades & Accessories)
        |
        v
[Product Card / Recommendations] -> (Review scores, stock status, and explainability tags)
        |
        v
[Add to Cart] -------------------> (Authenticated request, server validates stock)
        |
        v
[Cart Drawer Review] ------------> (Server computes authoritative subtotal and total)
        |
        v
[Initiate Checkout] -------------> (Backend creates internal order in pending_payment status)
        |
        v
[Razorpay Payment Modal] --------> (Customer selects Test Card / Netbanking / UPI)
        |
        v
[Payment Settlement] ------------> (Backend cryptographically verifies HMAC-SHA256 signature)
        |
        v
[Order Confirmation & Receipt] --> (Order marked paid, stock decremented, cart cleared)
        |
        v
[Customer Order History] --------> (Review past orders, line items, and itemized receipts)
```

---

## 8. Agent Commerce Journey

An external autonomous software agent interacts with the platform via the machine-to-machine protocol:

```
[External Autonomous Agent]
        |
        v (HTTP POST with X-Agent-Key header)
[FastAPI Gateway] ---------------> (Constant-time key verification via hmac.compare_digest)
        |
        v
[POST /api/agent-commerce/discover] (Structured catalog search matching agent constraints)
        |
        v
[POST /api/agent-commerce/inventory/check] (Validates stock availability for target items)
        |
        v
[POST /api/agent-commerce/cart/items] (Assembles items into server-calculated active cart)
        |
        v
[POST /api/agent-commerce/orders] (Creates authoritative order; idempotent on duplicate calls)
        |
        v
[POST /api/agent-commerce/payments/initiate] (Generates Razorpay test order & payment reference)
        |
        v
[Payment Link Provided to User] -> (Human authorizes payment or completes test transaction)
        |
        v
[Razorpay Webhook Callback] -----> (Backend verifies X-Razorpay-Signature and marks order paid)
```

---

## 9. Project Scope and Boundaries

### What the Platform Implements
- Full backend application with 11 API router modules and 26 endpoints.
- Relational schema with 8 database tables, foreign keys, check constraints, and Alembic migrations.
- Complete frontend single-page application with responsive catalog, AI assistant, cart drawer, Razorpay modal, and order history.
- 391 automated backend tests across 30 test files with 100% pass rate.
- 94 automated frontend tests across 11 test suites with 100% pass rate.
- 108 Postman/Newman automated API assertions.
- Multi-stage Docker containerization and Docker Compose orchestration.
- GitHub Actions continuous integration pipeline.

### What the Platform Explicitly Does Not Implement
- Live monetary transactions: All payment flows operate in Razorpay Test Mode with test keys. Real money movement requires merchant onboarding and KYC completion.
- Multi-merchant marketplace tenancy: The data models associate products with a merchant, but the storefront is configured as a single-merchant operational model.
- Autonomous credit line drawdown: Agents cannot charge credit cards or bank accounts autonomously; payment initialization produces checkout references requiring explicit customer settlement.
