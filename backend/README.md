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
│   │   ├── payments.py
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
│   │   ├── payment.py
│   │   ├── product.py
│   │   ├── order.py
│   │   └── order_item.py
│   ├── schemas/
│   │   ├── agent.py
│   │   ├── cart.py
│   │   ├── growth.py
│   │   ├── order.py
│   │   ├── payment.py
│   │   └── product.py
│   ├── services/
│   │   ├── ai_agent.py
│   │   ├── cart_service.py
│   │   ├── growth_service.py
│   │   ├── order_service.py
│   │   ├── payment_service.py
│   │   ├── product_service.py
│   │   ├── razorpay_service.py
│   │   └── recommendation_service.py
│   └── main.py
├── tests/
│   ├── test_agent_api.py
│   ├── test_cart_order_api.py
│   ├── test_database_health.py
│   ├── test_growth_api.py
│   ├── test_health.py
│   ├── test_models.py
│   ├── test_payment_api.py
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
- `RAZORPAY_KEY_ID`: Razorpay Test Mode Key ID (e.g. `rzp_test_...`)
- `RAZORPAY_KEY_SECRET`: Razorpay Test Mode Key Secret
- `RAZORPAY_CURRENCY`: `INR` (default)

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

### 2. Payment APIs (Step 2.10)

#### `POST /api/payments/create-order`
Creates a Razorpay Test Mode checkout order for an existing application order:
- **Price Security**: Client-supplied amounts are strictly rejected/ignored; payable total is read from the authoritative backend `Order.total`.
- **Eligibility Validation**: Ensures order is in `pending_payment` or `created` state and belongs to the customer.
- **Conversion**: Converts total to currency subunits (paise for INR, e.g. ₹4999.00 $\rightarrow$ 499900 paise).
- **Persistence**: Persists `Payment` record and attaches `razorpay_order_id` to `Order`.
- **Response**: Returns `payment_id`, `order_id`, `razorpay_order_id`, `amount`, `amount_in_paise`, `currency`, `key_id`, `status`.

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/payments/create-order" \
  -H "Content-Type: application/json" \
  -d '{"order_id": "c96e09cf-3910-45ec-a4ea-c7e102f2f84f", "customer_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c"}'
```

---

### 3. Cart APIs

#### `POST /api/cart`
Create or retrieve the active cart for a customer.

#### `GET /api/cart/{customer_id}`
Retrieve the customer's current active cart with line items, quantities, and server-side calculated totals.

#### `POST /api/cart/{customer_id}/items`
Add a product to the active cart with automatic quantity deduplication and inventory validation.

#### `PUT /api/cart/{customer_id}/items/{product_id}`
Update item quantity in cart. Revalidates stock and recalculates line totals and cart totals.

#### `DELETE /api/cart/{customer_id}/items/{product_id}`
Remove an item from active cart and recalculate subtotal and total.

---

### 4. Order APIs

#### `POST /api/orders`
Create an order by converting the customer's active cart into a `pending_payment` order with immutable snapshots of product name, SKU, and unit price.

#### `GET /api/orders/{customer_id}`
List all orders placed by the customer, sorted by creation date descending.

#### `GET /api/orders/{customer_id}/{order_id}`
Retrieve details for a specific order.

---

### 5. AI Agent Endpoints

#### `POST /api/agent/understand`
Converts customer natural language shopping requests into structured shopping intent without performing catalog search.

#### `POST /api/agent/search`
End-to-end AI agent product discovery translating natural language queries into filtered catalog search results.

#### `POST /api/agent/recommend`
AI Recommendation Engine endpoint scoring and ranking product candidates using multi-factor deterministic scoring.

#### `POST /api/agent/growth`
AI Growth Engine endpoint generating **Upsell** and **Cross-sell** opportunities.

---

### 6. Product Discovery Endpoints

#### `GET /api/products`
List active products with filtering, search, and pagination.

#### `GET /api/products/{product_id}`
Retrieve full product details by UUID. Returns `404 Not Found` if the product does not exist.

---

## Interactive Documentation

- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Interactive ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
