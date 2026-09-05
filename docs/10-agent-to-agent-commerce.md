# Agent-to-Agent (A2A) Commerce Protocol

## 1. Overview

The Agent-to-Agent (A2A) Commerce subsystem provides a secure, machine-to-machine interface allowing external autonomous software agents to discover catalog products, verify inventory availability, assemble carts, and programmatically initialize checkout on behalf of human users.

Rather than scraping dynamic HTML pages or simulating browser clicks, buyer agents communicate with dedicated, structured JSON endpoints under `/api/agent-commerce/*`.

The implementation is located across:
- `backend/app/services/agent_commerce_service.py`
- `backend/app/api/agent_commerce.py`
- `backend/app/schemas/agent_commerce.py`

---

## 2. The External Agent Trust Model

```
+-------------------------------------------------------------------------+
|                        UNTRUSTED EXTERNAL ZONE                          |
|                                                                         |
|   +-----------------------------------------------------------------+   |
|   | External Autonomous Buyer Agent (Procurement Agent, Assistant)  |   |
|   | - Holds valid X-Agent-Key                                       |   |
|   | - Untrusted execution environment                               |   |
|   +-----------------------------------------------------------------+   |
+------------------------------------|------------------------------------+
                                     | HTTP REST with X-Agent-Key
                                     v
+-------------------------------------------------------------------------+
|                       SECURITY PERIMETER (GATEWAY)                      |
|                                                                         |
|   1. Constant-time key comparison (hmac.compare_digest)                 |
|   2. Rate limiting & request size bounds                                |
|   3. Input schema validation (Pydantic v2)                              |
+------------------------------------|------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  BACKEND-AUTHORITATIVE COMMERCE ENGINE                  |
|                                                                         |
|   - Rejection of agent-supplied prices, discounts, and subtotals        |
|   - Transactional real-time inventory validation                        |
|   - Idempotent order assembly and payment link generation               |
|   - Strict payment boundary: Agents CANNOT mark orders as paid          |
+-------------------------------------------------------------------------+
```

### Core Security Principle: External Agent != Trusted Client
An external agent holding an `X-Agent-Key` is an authenticated machine client, but it is **not** a trusted administrative client. The system enforces strict boundaries:
1. Pricing Authority: The agent cannot dictate unit prices, discounts, or line totals. All monetary calculations are performed server-side from PostgreSQL records.
2. Inventory Authority: The agent cannot bypass stock constraints. Requests exceeding available inventory are rejected.
3. Payment Boundary: The agent cannot mark an order as paid or execute arbitrary payment settlement. The agent receives only a Razorpay payment order reference and checkout link. Final order completion requires cryptographic signature verification or an authentic Razorpay webhook.

---

## 3. Machine Authentication via `X-Agent-Key`

All endpoints under `/api/agent-commerce/*` require the `X-Agent-Key` HTTP header.

### Constant-Time Verification
To prevent timing side-channel attacks (where an attacker measures microsecond response variations to guess key bytes sequentially), the backend validates the header using Python's `hmac.compare_digest`:

```python
import hmac
from fastapi import Header, HTTPException, status
from app.core.config import settings

def verify_agent_api_key(x_agent_key: str = Header(None, alias="X-Agent-Key")) -> str:
    if not x_agent_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required 'X-Agent-Key' header.",
        )
    
    expected_key = settings.COMMERCE_AGENT_KEY
    if not hmac.compare_digest(x_agent_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent API key.",
        )
    return x_agent_key
```

In production mode, `COMMERCE_AGENT_KEY` must have a minimum length of 16 characters and cannot match insecure development placeholders.

---

## 4. End-to-End A2A Interaction Flow

```
Autonomous Buyer Agent             FastAPI Gateway (/api/agent-commerce)             Database / Razorpay
         |                                           |                                      |
         |-- 1. POST /discover --------------------->|                                      |
         |   (query: "GaN charger under 2000")       |-- 2. Query products matching intent -|
         |<- 3. AgentDiscoveryResponse --------------|                                      |
         |      (matching catalog items & prices)    |                                      |
         |                                           |                                      |
         |-- 4. POST /inventory/check -------------->|                                      |
         |   (product_id, quantity: 2)               |-- 5. Check Product.inventory ------->|
         |<- 6. AgentInventoryCheckResponse ---------|                                      |
         |      (is_available: true, in_stock: 45)   |                                      |
         |                                           |                                      |
         |-- 7. POST /cart ------------------------->|                                      |
         |   (customer_id)                           |-- 8. Get or create active cart ----->|
         |<- 9. CartResponse (cart_id) --------------|                                      |
         |                                           |                                      |
         |-- 10. POST /cart/items ------------------>|                                      |
         |    (cart_id, product_id, quantity)        |-- 11. Authoritative price & stock -->|
         |<- 12. CartResponse (authoritative total) -|                                      |
         |                                           |                                      |
         |-- 13. POST /orders ---------------------->|                                      |
         |    (cart_id, customer_id)                 |-- 14. Convert cart to Order -------->|
         |                                           |       (status: pending_payment)      |
         |<- 15. OrderResponse (order_id, total) ----|                                      |
         |                                           |                                      |
         |-- 16. POST /payments/initiate ----------->|                                      |
         |    (order_id)                             |-- 17. Create Razorpay Test Order --->|
         |<- 18. PaymentOrderResponse ---------------|                                      |
         |    (razorpay_order_id, amount_in_paise)   |                                      |
         |                                           |                                      |
         |-- 19. Forward Payment Link to User ------>|                                      |
         |    (User completes settlement)            |<- 20. Razorpay Webhook (Paid) -------|
```

---

## 5. Dedicated A2A API Endpoints

### 5.1 Catalog Discovery (`POST /api/agent-commerce/discover`)
Accepts a natural-language shopping query, parses intent and constraints, and queries matching products.
- Request:
  ```json
  {
    "message": "Heavy duty braided USB-C cable",
    "page": 1,
    "page_size": 5
  }
  ```
- Response (`200 OK`): Returns `AgentDiscoveryResponse` containing extracted intent, total matches, and product items with SKUs, prices, inventory levels, and specifications.

### 5.2 Product Details (`GET /api/agent-commerce/products/{product_id}`)
Retrieves authoritative product details, live stock levels, and technical attributes for a single product UUID.

### 5.3 Inventory Verification (`POST /api/agent-commerce/inventory/check`)
Enables agents to perform pre-flight stock validation before assembling carts or presenting options to users.
- Request:
  ```json
  {
    "product_id": "p1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
    "quantity": 3
  }
  ```
- Response (`200 OK`):
  ```json
  {
    "product_id": "p1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
    "product_name": "PowerArc 100W Braided Cable",
    "requested_quantity": 3,
    "is_available": true,
    "current_inventory": 48
  }
  ```

### 5.4 Cart Management (`POST /api/agent-commerce/cart` and `POST /api/agent-commerce/cart/items`)
- `POST /cart`: Initializes or retrieves an active cart for the target customer UUID.
- `POST /cart/items`: Adds a product to the cart with server-side inventory checks. Returns updated cart subtotals and line totals.

### 5.5 Idempotent Order Creation (`POST /api/agent-commerce/orders`)
Converts an active agent cart into an authoritative order:
```json
{
  "cart_id": "c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
  "customer_id": "u1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c"
}
```
**Idempotency Guarantee**: If an agent experiences a network timeout and resubmits the same `cart_id`, the service checks if an order already exists for that cart. If found, it returns the existing order immediately (`201 Created`) rather than assembling a duplicate order or decrementing stock twice.

### 5.6 Payment Initiation (`POST /api/agent-commerce/payments/initiate`)
Creates a Razorpay Test Mode checkout order for the internal application order.
- Reads `Order.total` directly from the database (client amount is strictly ignored).
- Returns `razorpay_order_id`, `amount_in_paise`, and public `key_id`.
- External agents present this checkout payload to the human buyer or client interface to execute authorization.

---

## 6. Audit Trail and Forensics

All A2A interactions are recorded in the `audit_logs` table with `event_type="AGENT_REQUEST"`:
- Captures agent action (`discover_products`, `check_inventory`, `agent_add_to_cart`, `agent_create_order`, `agent_initiate_payment`).
- Records sanitized payload metadata, target resource UUIDs, and execution status (`success`, `rejected`, `failed`).
- Ensures complete visibility into autonomous agent operations for store operators.
