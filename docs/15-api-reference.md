# API Reference

## 1. Overview

The AI Commerce Agent Platform provides a RESTful HTTP API documented with OpenAPI v3 standards. All requests and responses use JSON format with UTF-8 encoding. Standard HTTP status codes are returned for success and error conditions.

### Base URLs
- Local Development: `http://127.0.0.1:8000`
- Docker Compose: `http://localhost:8000`

### Authentication Schemes
- Bearer JWT: Standard header `Authorization: Bearer <access_token>` containing user ID and RBAC role.
- Machine Agent Key: Custom header `X-Agent-Key: <api_key>` verified via constant-time comparison.
- Webhook Signature: Custom header `X-Razorpay-Signature: <signature>` containing HMAC-SHA256 hash.

---

## 2. Authentication Endpoints

### 2.1 User Registration
- Path: `POST /api/auth/register`
- Purpose: Register a new customer account.
- Auth: None (Public)
- Request Body:
  ```json
  {
    "email": "customer@example.com",
    "password": "SecurePassword123"
  }
  ```
- Response (`201 Created`):
  ```json
  {
    "id": "u1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
    "email": "customer@example.com",
    "role": "customer",
    "is_active": true,
    "created_at": "2026-09-04T12:00:00Z"
  }
  ```
- Errors: `400 Bad Request` (Email already registered or invalid format).

### 2.2 User Login
- Path: `POST /api/auth/login`
- Purpose: Authenticate credentials and receive a JWT access token.
- Auth: None (Public)
- Request Body:
  ```json
  {
    "email": "customer@example.com",
    "password": "SecurePassword123"
  }
  ```
- Response (`200 OK`):
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "expires_in": 3600
  }
  ```
- Errors: `401 Unauthorized` (Invalid email or password).

### 2.3 User Profile
- Path: `GET /api/auth/me`
- Purpose: Retrieve the profile of the currently authenticated user.
- Auth: Bearer JWT (`customer`, `merchant`, `admin`)
- Response (`200 OK`):
  ```json
  {
    "id": "u1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
    "email": "customer@example.com",
    "role": "customer",
    "is_active": true,
    "created_at": "2026-09-04T12:00:00Z"
  }
  ```
- Errors: `401 Unauthorized`.

---

## 3. Product Catalog Endpoints

### 3.1 List Products
- Path: `GET /api/products`
- Purpose: Browse and filter active catalog products.
- Auth: None (Public)
- Query Parameters:
  - `search` (string, optional): Substring match on name/description.
  - `category` (string, optional): Category filter.
  - `min_price` (float, optional): Minimum price threshold.
  - `max_price` (float, optional): Maximum price threshold.
  - `available` (boolean, optional, default: true): In-stock only.
  - `page` (int, optional, default: 1): Page index.
  - `page_size` (int, optional, default: 20): Items per page.
- Response (`200 OK`):
  ```json
  {
    "items": [
      {
        "id": "p1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
        "merchant_id": "m1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
        "name": "Keychron K2 Mechanical Keyboard",
        "description": "Compact 75% layout with RGB backlighting.",
        "category": "Computer Accessories",
        "price": "4499.00",
        "currency": "INR",
        "inventory": 25,
        "sku": "ACC-KB-K2",
        "attributes": {"switch": "Gateron Brown", "layout": "75%"},
        "is_active": true,
        "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3",
        "created_at": "2026-09-01T00:00:00Z",
        "updated_at": "2026-09-01T00:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
  ```

### 3.2 Get Product Details
- Path: `GET /api/products/{id}`
- Purpose: Retrieve full product specifications for a specific UUID.
- Auth: None (Public)
- Response (`200 OK`): Product details object.
- Errors: `404 Not Found`.

### 3.3 Create Product
- Path: `POST /api/products`
- Purpose: Add a new product to the catalog.
- Auth: Bearer JWT (`merchant`, `admin`)
- Request Body: Product create schema.
- Response (`201 Created`): Created product object.
- Errors: `400 Bad Request`, `403 Forbidden`.

### 3.4 Update Product
- Path: `PUT /api/products/{id}`
- Purpose: Update product details or adjust inventory.
- Auth: Bearer JWT (`merchant`, `admin`)
- Response (`200 OK`): Updated product object.
- Errors: `400 Bad Request`, `403 Forbidden`, `404 Not Found`.

### 3.5 Delete Product
- Path: `DELETE /api/products/{id}`
- Purpose: Soft delete or remove a product from the catalog.
- Auth: Bearer JWT (`merchant`, `admin`)
- Response (`200 OK`): Deletion confirmation.
- Errors: `403 Forbidden`, `404 Not Found`.

---

## 4. AI Shopping Assistant Endpoints

### 4.1 Understand Intent
- Path: `POST /api/agent/understand`
- Purpose: Parse unstructured text into structured shopping parameters.
- Auth: None (Public)
- Request Body: `{"message": "Mechanical keyboard under 5000"}`
- Response (`200 OK`): `AgentUnderstandResponse` containing message and `ShoppingIntent`.

### 4.2 Conversational Search
- Path: `POST /api/agent/search`
- Purpose: End-to-end natural-language catalog search.
- Auth: None (Public)
- Request Body: `{"message": "Mechanical keyboard under 5000", "page": 1, "page_size": 10}`
- Response (`200 OK`): `AgentSearchResponse` with extracted intent and matching items.

### 4.3 Multi-Factor Scored Recommendations
- Path: `POST /api/agent/recommend`
- Purpose: Generate ranked product recommendations with scores and explainability.
- Auth: None (Public / Optional JWT)
- Request Body: `{"message": "Ergonomic mouse for office work", "page": 1, "page_size": 10}`
- Response (`200 OK`): `AgentRecommendResponse` containing items with `score` (0.0 to 1.0) and `reason`.

### 4.4 Growth Opportunities (Upsell & Cross-Sell)
- Path: `POST /api/agent/growth`
- Purpose: Surfacing higher-tier alternatives and companion accessories.
- Auth: None (Public / Optional JWT)
- Request Body: `{"message": "Keychron mechanical keyboard", "page": 1, "page_size": 10}`
- Response (`200 OK`): `AgentGrowthResponse` containing `primary_products`, `upsell`, and `cross_sell` arrays.

---

## 5. Cart Management Endpoints

### 5.1 View Cart
- Path: `GET /api/cart`
- Purpose: Retrieve the active shopping cart for the authenticated customer.
- Auth: Bearer JWT (`customer`)
- Response (`200 OK`): `CartResponse` with items, item count, subtotal, and total.

### 5.2 Add Item to Cart
- Path: `POST /api/cart/items`
- Purpose: Add a product to the cart with server-side inventory verification.
- Auth: Bearer JWT (`customer`)
- Request Body:
  ```json
  {
    "product_id": "p1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
    "quantity": 1
  }
  ```
- Response (`200 OK`): Updated `CartResponse`.
- Errors: `400 Bad Request` (Insufficient inventory or inactive product), `404 Not Found`.

### 5.3 Update Item Quantity
- Path: `PUT /api/cart/items/{product_id}`
- Purpose: Modify the quantity of a product in the active cart.
- Auth: Bearer JWT (`customer`)
- Request Body: `{"quantity": 3}`
- Response (`200 OK`): Updated `CartResponse`.
- Errors: `400 Bad Request`, `404 Not Found`.

### 5.4 Remove Item from Cart
- Path: `DELETE /api/cart/items/{product_id}`
- Purpose: Remove a product line item from the cart.
- Auth: Bearer JWT (`customer`)
- Response (`200 OK`): Updated `CartResponse`.
- Errors: `404 Not Found`.

### 5.5 Clear Cart
- Path: `DELETE /api/cart`
- Purpose: Empty all items from the active cart.
- Auth: Bearer JWT (`customer`)
- Response (`200 OK`): Empty `CartResponse` with zero totals.

---

## 6. Order Management Endpoints

### 6.1 Create Order
- Path: `POST /api/orders`
- Purpose: Convert active cart items into an authoritative order in `pending_payment` status.
- Auth: Bearer JWT (`customer`)
- Request Body: `{}` (or optional `{"cart_id": "..."}`)
- Response (`201 Created`): `OrderResponse` containing order reference, items, and totals.
- Errors: `400 Bad Request` (Empty cart, inactive items, or insufficient stock).

### 6.2 Customer Order History
- Path: `GET /api/orders`
- Purpose: List all historical orders belonging to the authenticated customer.
- Auth: Bearer JWT (`customer`)
- Response (`200 OK`): Array of `OrderResponse` objects sorted newest first.

### 6.3 Get Order Details and Receipt
- Path: `GET /api/orders/{id}`
- Purpose: Retrieve full order details and itemized receipt.
- Auth: Bearer JWT (`customer` for own order, or `admin`)
- Response (`200 OK`): `OrderResponse` with full item breakdown.
- Errors: `404 Not Found` (Order does not exist or belongs to another customer).

---

## 7. Payment Endpoints

### 7.1 Create Payment Order
- Path: `POST /api/payments/create-order`
- Purpose: Create a Razorpay Test Mode checkout order for an internal order.
- Auth: Bearer JWT (`customer`)
- Request Body: `{"order_id": "7b8c9d0e-1f2a-3b4c-5d6e-7f8a9b0c1d2e"}`
- Response (`200 OK`):
  ```json
  {
    "payment_id": "9e0f1a2b-3c4d-5e6f-7a8b-9c0d1e2f3a4b",
    "order_id": "7b8c9d0e-1f2a-3b4c-5d6e-7f8a9b0c1d2e",
    "razorpay_order_id": "order_OZ1234567890",
    "amount": "4499.00",
    "amount_in_paise": 449900,
    "currency": "INR",
    "key_id": "rzp_test_placeholder",
    "status": "created",
    "created_at": "2026-09-04T12:00:00Z"
  }
  ```
- Errors: `400 Bad Request` (Order already paid), `403 Forbidden`, `404 Not Found`.

### 7.2 Webhook Handler
- Path: `POST /api/payments/webhook`
- Purpose: Process asynchronous Razorpay payment events (`payment.captured`, `order.paid`).
- Headers: `X-Razorpay-Signature: <hmac_sha256_hex>`
- Request Body: Raw JSON payload from Razorpay.
- Response (`200 OK`): Status confirmation (`{"status": "ok"}`).
- Errors: `400 Bad Request` (Invalid or missing signature).

---

## 8. Agent-to-Agent (A2A) Endpoints

All endpoints require the `X-Agent-Key` HTTP header.

| Method | Path | Request Schema | Response Schema | Description |
|---|---|---|---|---|
| `POST` | `/api/agent-commerce/discover` | `AgentDiscoveryRequest` | `AgentDiscoveryResponse` | Discover catalog products via natural-language query |
| `GET` | `/api/agent-commerce/products/{id}` | None | `AgentProductDetailResponse` | Retrieve authoritative product specs and stock |
| `POST` | `/api/agent-commerce/inventory/check`| `AgentInventoryCheckRequest` | `AgentInventoryCheckResponse` | Verify real-time inventory for target item |
| `POST` | `/api/agent-commerce/cart` | `CartCreateRequest` | `CartResponse` | Initialize or retrieve active agent cart |
| `POST` | `/api/agent-commerce/cart/items` | `AgentCartItemRequest` | `CartResponse` | Add product to agent cart |
| `POST` | `/api/agent-commerce/orders` | `AgentOrderCreateRequest` | `OrderResponse` | Idempotently convert cart to Order |
| `POST` | `/api/agent-commerce/payments/initiate`| `AgentPaymentInitiateRequest`| `PaymentOrderResponse` | Create Razorpay test payment order |

---

## 9. Merchant Dashboard Endpoints

Require `Bearer JWT` with role `merchant` or `admin`.

| Method | Path | Response Schema | Description |
|---|---|---|---|
| `GET` | `/api/dashboard/overview` | `OverviewMetricsResponse` | Aggregated revenue, AOV, conversion rate, and AI metrics |
| `GET` | `/api/dashboard/orders` | `DashboardOrdersResponse` | Recent merchant orders with live payment statuses |
| `GET` | `/api/dashboard/activity` | `DashboardActivityResponse` | Real-time audit events and agent activity feed |

---

## 10. Audit and Administrative Endpoints

| Method | Path | Auth / Role | Description |
|---|---|---|---|
| `GET` | `/api/audit/admin/all` | Bearer JWT (`admin`) | Platform-wide audit log query |
| `GET` | `/api/audit/{customer_id}` | Bearer JWT (`customer`, `admin`) | Customer activity audit query |
| `GET` | `/api/admin/system/status` | Bearer JWT (`admin`) | Database connectivity and role distribution |
| `GET` | `/api/admin/audit-logs` | Bearer JWT (`admin`) | System audit logs query |

---

## 11. Health and Liveness Endpoints

| Method | Path | Auth | Description | Response Example |
|---|---|---|---|---|
| `GET` | `/api/health` | None (Public) | API server liveness check | `{"status": "ok", "service": "ai-commerce-agent-api"}` |
| `GET` | `/api/health/database` | None (Public) | Database connectivity check | `{"status": "ok", "database": "connected"}` |
