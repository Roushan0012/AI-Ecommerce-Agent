# Audit Logging and Observability

## 1. Overview

The AI Commerce Agent Platform implements an append-only, relational audit logging architecture stored in the PostgreSQL `audit_logs` table. In an autonomous commerce environment where decisions are influenced by conversational intent classifiers, recommendation scoring engines, and external software agents, complete auditability is essential for financial reconciliation, dispute resolution, security monitoring, and regulatory compliance.

The audit subsystem is implemented in:
- `backend/app/models/audit_log.py`
- `backend/app/services/audit_service.py`
- `backend/app/api/audit.py`
- `backend/app/api/admin.py`

---

## 2. Why Auditability Matters in AI Commerce

In traditional e-commerce, user actions map to discrete button clicks. In an AI-assisted and autonomous agent commerce platform, additional layers of complexity require forensic visibility:
1. Explainability and Dispute Resolution: If a shopper questions why a specific product was recommended or added to cart, the audit log records the exact prompt, detected intent, candidate scores, and explainability rationale.
2. Financial Non-Repudiation: Every payment initiation, gateway response, webhook callback, and signature verification is permanently logged, providing an immutable paper trail for chargebacks and bank reconciliations.
3. Autonomous Agent Monitoring: Machine-to-machine transactions conducted via `X-Agent-Key` are tagged and tracked separately, enabling store operators to monitor agent behavior, query patterns, and conversion rates.
4. Security Incident Investigation: Failed authentications, rate limit violations, parameter tampering attempts, and currency/amount mismatches emit `SECURITY_VIOLATION` events for rapid threat detection.

---

## 3. Relational Schema of `audit_logs`

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    customer_id UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id VARCHAR(255),
    event_type VARCHAR(100) NOT NULL,
    action VARCHAR(255),
    payload JSON,
    result JSON,
    status VARCHAR(50) NOT NULL DEFAULT 'success',
    error_message TEXT,
    cart_id UUID REFERENCES carts(id) ON DELETE SET NULL,
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    payment_id UUID REFERENCES payments(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_audit_logs_customer_id ON audit_logs (customer_id);
CREATE INDEX ix_audit_logs_event_type ON audit_logs (event_type);
CREATE INDEX ix_audit_logs_status ON audit_logs (status);
CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);
```

### Column Specifications
- `id`: UUID primary key.
- `customer_id`: Optional UUID referencing the user account responsible for the action.
- `session_id`: Optional client or agent session identifier.
- `event_type`: High-level category classification (e.g., `USER_REQUEST`, `PAYMENT_EVENT`, `RECOMMENDATION`).
- `action`: Specific operation performed (e.g., `create_order`, `add_item_to_cart`, `payment_verified_and_paid`).
- `payload`: Sanitized JSON representation of the input parameters.
- `result`: Sanitized JSON representation of the operation outcome.
- `status`: Execution status (`'success'`, `'failed'`, `'rejected'`).
- `error_message`: Detailed exception or error description if the operation failed.
- `cart_id`, `order_id`, `payment_id`: Foreign key pointers linking the log record to the affected commerce entities.
- `created_at`: Immutable UTC timestamp with timezone.

---

## 4. Standardized Event Classifications

| Event Type | Typical Actions | Emitted By | Payload / Result Details |
|---|---|---|---|
| `USER_REQUEST` | `understand_intent`, `agent_search`, `agent_recommend`, `agent_growth` | `api/agent.py` | Sanitized user prompt, requested page, and page size |
| `INTENT_DETECTED` | `understand_intent` | `api/agent.py` | Extracted `ShoppingIntent` (category, budget bounds, attributes) |
| `TOOL_RESULT` | `product_search` | `api/agent.py` | Query parameters and total matched catalog items |
| `RECOMMENDATION` | `recommend_products`, `growth_recommendations` | `api/agent.py` | Recommendation counts, upsell/cross-sell breakdown |
| `CART_UPDATED` | `add_item_to_cart`, `update_item_quantity`, `remove_item` | `services/cart_service.py` | Product ID, quantity change, updated cart total |
| `ORDER_CREATED` | `create_order` | `services/order_service.py` | Cart ID, item count, order UUID, order total |
| `PAYMENT_EVENT` | `create_payment_order`, `payment_verified_and_paid` | `services/payment_service.py` | Razorpay order ID, payment ID, amount, order status |
| `AGENT_REQUEST` | `discover_products`, `check_inventory`, `agent_create_order` | `services/agent_commerce_service.py` | Machine agent query, requested SKU/quantity, order UUID |
| `SECURITY_VIOLATION` | `webhook_amount_mismatch`, `webhook_currency_mismatch` | `services/payment_service.py` | Expected vs received amounts, currency discrepancies |
| `ERROR` | System exceptions, provider timeouts | Application services | Exception message, stack context (sanitized) |

---

## 5. Append-Only Immutability Guarantee

The audit subsystem is designed as an **append-only** data store:
- No UPDATE routes exist: Neither the public API, merchant dashboard, nor administrative routes expose endpoints to modify existing audit records.
- No DELETE routes exist: Audit records cannot be deleted via the API.
- Database Constraints: Database rows can only be written through `audit_service.record_event()`. Foreign keys to carts, orders, and payments utilize `ON DELETE SET NULL`, ensuring that even if an entity is removed, the historical audit entry persists intact.

---

## 6. Audit Trail Access Endpoints

### 6.1 Platform-Wide Administrative Audit Logs (`GET /api/audit/admin/all` and `GET /api/admin/audit-logs`)
- Restricted to users possessing the `admin` role.
- Supports filtering by `event_type` and pagination via `page` and `page_size`.
- Returns total record counts and chronological log entries.

### 6.2 Customer Audit Trail (`GET /api/audit/{customer_id}`)
- Allows authenticated customers to inspect their own activity history.
- Enforces ownership verification: `customer_id` must match `current_user.id` (or the requesting user must be an `admin`).
- Returns all conversational requests, cart updates, orders, and payment events belonging to that customer.

---

## 7. Sample Audit Record

```json
{
  "id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
  "customer_id": "u1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
  "session_id": null,
  "event_type": "PAYMENT_EVENT",
  "action": "payment_verified_and_paid",
  "payload": {
    "event": "payment.captured",
    "razorpay_order_id": "order_OZ1234567890",
    "razorpay_payment_id": "pay_PZ1234567890"
  },
  "result": {
    "order_status": "paid",
    "payment_status": "paid"
  },
  "status": "success",
  "error_message": null,
  "cart_id": "c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
  "order_id": "7b8c9d0e-1f2a-3b4c-5d6e-7f8a9b0c1d2e",
  "payment_id": "9e0f1a2b-3c4d-5e6f-7a8b-9c0d1e2f3a4b",
  "created_at": "2026-09-04T12:01:30.123456Z"
}
```
