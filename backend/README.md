# AI Commerce Agent - Backend API

FastAPI backend service for the Razorpay AI Buildathon Track 01 "AI Commerce Agent".

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── agent.py
│   │   ├── cart.py
│   │   ├── orders.py
│   │   └── products.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── migrate.py
│   │   ├── prompts.py
│   │   └── seed.py
│   ├── models/
│   │   ├── cart.py
│   │   ├── cart_item.py
│   │   ├── merchant.py
│   │   ├── product.py
│   │   ├── order.py
│   │   └── order_item.py
│   ├── schemas/
│   │   ├── agent.py
│   │   ├── cart.py
│   │   ├── growth.py
│   │   ├── order.py
│   │   └── product.py
│   ├── services/
│   │   ├── ai_agent.py
│   │   ├── cart_service.py
│   │   ├── growth_service.py
│   │   ├── order_service.py
│   │   ├── product_service.py
│   │   └── recommendation_service.py
│   └── main.py
├── tests/
│   ├── test_agent_api.py
│   ├── test_cart_order_api.py
│   ├── test_database_health.py
│   ├── test_growth_api.py
│   ├── test_health.py
│   ├── test_models.py
│   ├── test_products_api.py
│   ├── test_recommendation_api.py
│   └── test_seed.py
├── .env.example
├── requirements.txt
└── README.md
```

## Getting Started

### 1. Create and Activate Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and configure your credentials:

```bash
cp .env.example .env
```

Available environment variables:
- `DATABASE_URL`: PostgreSQL connection string (e.g. `postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres`)
- `SUPABASE_URL`: Supabase project URL (optional)
- `SUPABASE_PUBLISHABLE_KEY`: Supabase anon/publishable key (optional)
- `AI_PROVIDER`: `mock` (default for deterministic offline tests) or `openai`, `groq`, `openrouter`
- `AI_MODEL`: Model name (e.g. `gpt-4o-mini`, `llama-3.3-70b-versatile`)
- `AI_API_KEY`: API key for external LLM provider (when using real provider)
- `AI_BASE_URL`: Optional custom OpenAI-compatible API base URL

> **Note**: `.env` contains sensitive credentials and is strictly excluded from Git.

### 4. Seed Product Catalog Data

Populate the demo merchant (`AI Commerce Demo Store`) and 14 realistic products across 4 categories (Audio, Computer Accessories, Chargers & Cables, Work & Travel):

```bash
python -m app.core.seed
```

> **Note**: The seed script is completely **idempotent**. Running it multiple times safely updates existing products by SKU without creating duplicates.

### 5. Run Database Migrations

```bash
python -m app.core.migrate
```

### 6. Run Tests

```bash
pytest
```

### 7. Run Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## API Endpoints

### 1. Health Endpoints
- `GET /api/health` — Basic service status
- `GET /api/health/database` — Supabase PostgreSQL database connectivity check

### 2. Cart APIs

#### `POST /api/cart`
Create or retrieve the active cart for a customer.

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/cart" \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c"}'
```

#### `GET /api/cart/{customer_id}`
Retrieve the customer's current active cart with line items, quantities, and server-side calculated totals.

#### `POST /api/cart/{customer_id}/items`
Add a product to the active cart.
- Authoritative product price is fetched server-side from the database. Client cannot supply `unit_price`.
- If the item already exists in the cart, its quantity is incremented without creating duplicate rows.
- Revalidates `quantity <= product.inventory`.

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/cart/c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c/items" \
  -H "Content-Type: application/json" \
  -d '{"product_id": "465206d3-bd4d-4f9f-b705-010670ab4006", "quantity": 2}'
```

#### `PUT /api/cart/{customer_id}/items/{product_id}`
Update item quantity in cart. Revalidates stock and recalculates line totals and cart totals.

#### `DELETE /api/cart/{customer_id}/items/{product_id}`
Remove an item from active cart and recalculate subtotal and total.

---

### 3. Order APIs

#### `POST /api/orders`
Create an order by converting the customer's active cart.
- **Atomic Transaction**: Re-verifies all products are active and in stock, re-reads authoritative unit prices, calculates total server-side, creates `Order` with `status: "pending_payment"`, creates `OrderItem` snapshots (storing product name, sku, and price), and marks the cart status as `"converted"`.

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/orders" \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c"}'
```

#### `GET /api/orders/{customer_id}`
List all orders placed by the customer, sorted by creation date descending.

#### `GET /api/orders/{customer_id}/{order_id}`
Retrieve details for a specific order. Rejects access if the order does not belong to the requested customer.

---

### 4. AI Agent Endpoints

#### `POST /api/agent/understand`
Converts customer natural language shopping requests into structured shopping intent without performing catalog search.

#### `POST /api/agent/search`
End-to-end AI agent product discovery translating natural language queries into filtered catalog search results.

#### `POST /api/agent/recommend`
AI Recommendation Engine endpoint scoring and ranking product candidates using multi-factor deterministic scoring.

#### `POST /api/agent/growth`
AI Growth Engine endpoint generating **Upsell** and **Cross-sell** opportunities.

---

### 5. Product Discovery Endpoints

#### `GET /api/products`
List active products with filtering, search, and pagination.

#### `GET /api/products/{product_id}`
Retrieve full product details by UUID. Returns `404 Not Found` if the product does not exist.

---

## Interactive Documentation

- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Interactive ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
