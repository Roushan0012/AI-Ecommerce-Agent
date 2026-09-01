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
