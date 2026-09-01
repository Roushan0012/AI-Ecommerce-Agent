# Phase 15 — Agent-to-Agent Commerce Specification

## 1. Overview
Agent-to-Agent Commerce provides a secure, machine-to-machine (M2M) API that allows external/buyer AI agents to discover products, check live inventory, manage carts, create orders, and initiate payments with the merchant's commerce backend.

```
Buyer Agent
    ↓ (HTTP + X-Agent-Key Header)
Agent Commerce Interface (/api/agent-commerce/*)
    ↓
Constant-Time Authentication & Input Validation
    ↓
Phase 12 Security Guardrails (Authoritative Pricing & Inventory)
    ↓
Existing Commerce Services (Cart, Order, Payment, Recommendations)
    ↓
PostgreSQL Database (Transactional Storage & Audit Trail)
```

## 2. Threat Model & Untrusted External Agent Principle
External buyer agents are treated as **untrusted clients**. The system strictly prevents:
1. **Direct Database Access**: No SQL injection or raw database credentials exposed.
2. **Price & Total Manipulation**: Client/agent-supplied prices, subtotals, and totals are ignored; prices are computed authoritatively from the database catalog.
3. **Inventory Bypass**: Atomically verified on item addition and order checkout.
4. **Payment Verification Bypass**: External agents cannot mark orders as `paid` or fake Razorpay confirmations. Only HMAC-SHA256 verified Razorpay webhooks can transition order status to `paid`.
5. **Cross-Customer Snooping**: Strict UUID tenant isolation enforced by `guardrails.validate_customer_ownership`.
6. **Prompt Injection**: All natural queries sanitized before AI intent extraction.

## 3. Machine-to-Machine Authentication
- **Header**: `X-Agent-Key`
- **Verification**: Constant-time comparison (`hmac.compare_digest`) against configured `COMMERCE_AGENT_KEY`.
- **Environment**: Configured in `.env` (documented in `.env.example`).
- **Failure**: Missing or invalid key immediately returns `401 Unauthorized`.

## 4. API Endpoints

| Endpoint | Method | Header | Description |
|---|---|---|---|
| `/api/agent-commerce/discover` | `POST` | `X-Agent-Key` | Semantic product discovery from natural language intent and budget constraints. |
| `/api/agent-commerce/products/{id}` | `GET` | `X-Agent-Key` | Authoritative product details, live stock, and server price. |
| `/api/agent-commerce/inventory/check` | `POST` | `X-Agent-Key` | Pre-checkout stock and purchase quantity verification. |
| `/api/agent-commerce/cart` | `POST` | `X-Agent-Key` | Get or create active session cart for the customer. |
| `/api/agent-commerce/cart/items` | `POST` | `X-Agent-Key` | Add product to cart with server-side pricing. |
| `/api/agent-commerce/orders` | `POST` | `X-Agent-Key` | Create order from cart with built-in idempotency protection. |
| `/api/agent-commerce/payments/initiate` | `POST` | `X-Agent-Key` | Initiate Razorpay Test Mode checkout order with authoritative amount. |

## 5. Idempotency & Safe Retries
Agent systems frequently retry requests across network hops. The order creation endpoint (`/api/agent-commerce/orders`) checks if an active order already exists for the given `cart_id` and `customer_id`. If found, it returns the existing order (`200 OK` / `201 Created`) rather than creating duplicate orders or triggering conflicting double-conversions.

## 6. Audit Trail & Observability
Every agent interaction produces structured `AuditLog` records:
- `AGENT_REQUEST` (Discover / Search queries)
- `CART_UPDATED` (Items added)
- `ORDER_CREATED` (Orders converted)
- `PAYMENT_EVENT` (Payment initiated / verified)
- `SECURITY_VIOLATION` (Unauthorized access / forged inputs)

All audit logs are scrubbed to redact API keys, tokens, and secrets, and are visualized on the **Phase 14 Merchant Dashboard**.
