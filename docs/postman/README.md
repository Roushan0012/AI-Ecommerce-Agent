# AI Commerce Agent API - Postman Documentation

This directory contains the Postman API collection for testing the FastAPI backend endpoints of the AI Commerce Agent.

## Collection Details

- **Collection Name**: `AI Commerce Agent API`
- **File**: `AI-Commerce-Agent-API.postman_collection.json`
- **Format**: Postman Collection v2.1.0

---

## 1. Start the FastAPI Server

Before executing requests in Postman, ensure the backend development server is running:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at `http://127.0.0.1:8000`.

---

## 2. Running Postman Collection via CLI (Newman)

To run the entire automated verification suite with Newman:

```bash
npx newman run docs/postman/AI-Commerce-Agent-API.postman_collection.json
```

---

## 3. Importing the Collection into Postman UI

1. Open **Postman**.
2. Click the **Import** button in the top left workspace navigation.
3. Choose **Files** and select `docs/postman/AI-Commerce-Agent-API.postman_collection.json` (or drag and drop the file into Postman).
4. Click **Import**. The `AI Commerce Agent API` collection will appear in your left sidebar.

---

## 4. Available Requests & Test Assertions

| # | Request Name | Method | URL | Description & Assertions |
|---|---|---|---|---|
| 1 | **Health Check** | `GET` | `/api/health` | Status 200, status = "ok", service = "ai-commerce-agent-api" |
| 2 | **Database Health Check** | `GET` | `/api/health/database` | Status 200, status = "ok", database = "connected" |
| 3 | **AI Agent - Understand Intent** | `POST` | `/api/agent/understand` | Status 200, extracts structured shopping intent (`intent`, `search_query`, `category`, `price bounds`) |
| 4 | **AI Agent - Search Products** | `POST` | `/api/agent/search` | Status 200, performs end-to-end intent understanding and product discovery |
| 5 | **AI Agent - Recommend Products** | `POST` | `/api/agent/recommend` | Status 200, scores and ranks candidate recommendations with explainability reasons |
| 6 | **AI Agent - Growth (Upsell & Cross-sell)** | `POST` | `/api/agent/growth` | Status 200, generates ranked higher-tier upsells and complementary companion cross-sells |
| 7 | **List Products (Default)** | `GET` | `/api/products` | Status 200, returns pagination object (`items`, `total`, `page`, `page_size`) |
| 8 | **Get Product Detail** | `GET` | `/api/products/:id` | Status 200, complete schema (`name`, `price`, `attributes`, `sku`, etc.) |
| 9 | **Filter Products by Category** | `GET` | `/api/products?category=Audio` | Status 200, all items match `category = Audio` |
| 10 | **Filter Products by Price Range** | `GET` | `/api/products?min_price=5000&max_price=20000` | Status 200, all items within [5000, 20000] |
| 11 | **Search Products** | `GET` | `/api/products?search=headphone` | Status 200, items match keyword in name/description |
| 12 | **Filter Available Products** | `GET` | `/api/products?available=true` | Status 200, all items active and in-stock (`inventory > 0`) |
| 13 | **Paginate Products** | `GET` | `/api/products?page=1&page_size=5` | Status 200, returns exactly 5 items for page 1 |
| 14 | **Get Product Detail (404)** | `GET` | `/api/products/00000000-0000-0000-0000-000000000000` | Status 404, detail = "Product not found" |
| 15 | **Cart - Create or Get Cart** | `POST` | `/api/cart` | Status 200, creates or retrieves active cart for customer |
| 16 | **Cart - Add Item** | `POST` | `/api/cart/:customer_id/items` | Status 200, adds item with authoritative server price and validates inventory |
| 17 | **Cart - Get Active Cart** | `GET` | `/api/cart/:customer_id` | Status 200, retrieves active cart with items and recalculated totals |
| 18 | **Cart - Update Item Quantity** | `PUT` | `/api/cart/:customer_id/items/:product_id` | Status 200, updates quantity, revalidates stock, and updates subtotal |
| 19 | **Cart - Remove Item** | `DELETE` | `/api/cart/:customer_id/items/:product_id` | Status 200, removes item and recalculates cart totals |
| 20 | **Cart - Add Product For Checkout** | `POST` | `/api/cart/:customer_id/items` | Status 200, primes active cart for order creation |
| 21 | **Orders - Create Order from Cart** | `POST` | `/api/orders` | Status 201, converts active cart into `pending_payment` order with price snapshots |
| 22 | **Orders - List Customer Orders** | `GET` | `/api/orders/:customer_id` | Status 200, lists all customer orders sorted descending |
| 23 | **Orders - Get Single Order Detail** | `GET` | `/api/orders/:customer_id/:order_id` | Status 200, returns order detail matching customer and order ID |
| 24 | **Payments - Create Razorpay Test Order** | `POST` | `/api/payments/create-order` | Status 200, creates Razorpay Test Mode checkout order with authoritative amount in paise |
| 25 | **Payments - Razorpay Webhook Verification** | `POST` | `/api/payments/webhook` | Status 200, verifies HMAC-SHA256 signature, validates payment/amount, marks order as paid |
| 26 | **Audit - Get Customer Audit Logs** | `GET` | `/api/audit/:customer_id` | Status 200, retrieves chronological audit events for customer |
| 27 | **Auth - User Registration** | `POST` | `/api/auth/register` | Status 201/409, registers user with safe customer role default |
| 28 | **Auth - User Login** | `POST` | `/api/auth/login` | Status 200, authenticates customer and saves `auth_token` |
| 29 | **Auth - Merchant Login** | `POST` | `/api/auth/login` | Status 200, authenticates merchant and saves `merchant_token` |
| 30 | **Auth - Admin Login** | `POST` | `/api/auth/login` | Status 200, authenticates admin and saves `admin_token` |
| 31 | **Dashboard - Overview Metrics** | `GET` | `/api/dashboard/overview` | Status 200, requires `merchant_token` (`require_merchant`) |
| 32 | **Dashboard - Recent Orders** | `GET` | `/api/dashboard/orders` | Status 200, requires `merchant_token` (`require_merchant`) |
| 33 | **Dashboard - Recent Activity** | `GET` | `/api/dashboard/activity` | Status 200, requires `merchant_token` (`require_merchant`) |
| 34-39 | **Agent Commerce Endpoints** | Various | `/api/agent-commerce/*` | Status 200/201, strictly requires `X-Agent-Key` header |
| 40-44 | **Adversarial Security Tests** | Various | Various | Price tampering discarded, negative quantity rejected, cross-user checkout blocked |
| 45-51 | **Role Authorization Tests** | Various | `/api/dashboard/*`, `/api/admin/*` | Verifies 401 unauthenticated, 403 customer access to merchant/admin, and 200 admin access |
| 52-54 | **A2A Boundary Isolation Tests** | Various | `/api/agent-commerce/*`, `/api/cart` | Verifies User/Admin JWT cannot access Agent Commerce (401) and X-Agent-Key cannot access User Cart (401) |

