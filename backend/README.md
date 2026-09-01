# AI Commerce Agent - Backend API

FastAPI backend service for the Razorpay AI Buildathon Track 01 "AI Commerce Agent".

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── agent.py
│   │   └── products.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── prompts.py
│   │   └── seed.py
│   ├── models/
│   │   ├── merchant.py
│   │   ├── product.py
│   │   ├── order.py
│   │   └── order_item.py
│   ├── schemas/
│   │   ├── agent.py
│   │   ├── growth.py
│   │   └── product.py
│   ├── services/
│   │   ├── ai_agent.py
│   │   ├── growth_service.py
│   │   ├── product_service.py
│   │   └── recommendation_service.py
│   └── main.py
├── tests/
│   ├── test_agent_api.py
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

### 5. Run Tests

```bash
pytest
```

### 6. Run Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## API Endpoints

### 1. Health Endpoints
- `GET /api/health` — Basic service status
- `GET /api/health/database` — Supabase PostgreSQL database connectivity check

### 2. AI Agent Endpoints

#### `POST /api/agent/understand`
Converts customer natural language shopping requests into structured shopping intent without performing catalog search.

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/agent/understand" \
  -H "Content-Type: application/json" \
  -d '{"message": "I need wireless headphones under ₹5000"}'
```

#### `POST /api/agent/search`
End-to-end AI agent product discovery:
1. Understands natural language customer message.
2. Extracts structured shopping intent (`search_query`, `category`, `price bounds`, `availability`).
3. Queries Supabase PostgreSQL catalog with translated filters.
4. Returns conversational summary, structured intent, and matching product items with pagination.

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/agent/search" \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me wireless earbuds under ₹5000"}'
```

#### `POST /api/agent/recommend`
AI Recommendation Engine endpoint that scores and ranks product candidates using multi-factor deterministic scoring:
- **Hard Constraints**: Products out-of-stock, inactive, or exceeding budget are excluded (score 0.0).
- **Category Alignment (30%)**: Matches category from extracted intent.
- **Keyword & Attribute Relevance (35%)**: Token matches across title, description, and JSONB attributes.
- **Price Fitness (20%)**: Proximity to requested budget without constraint violation.
- **Inventory Health (15%)**: Stock depth weighting.

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/agent/recommend" \
  -H "Content-Type: application/json" \
  -d '{"message": "I need wireless headphones under ₹5000 for travelling"}'
```

#### `POST /api/agent/growth`
AI Growth Engine endpoint that generates **Upsell** and **Cross-sell** opportunities:
- **Primary Products**: Identifies top product matches corresponding to customer query.
- **Upsell Opportunities**:
  - Recommends higher-tier products in the same category offering improved specifications (e.g. 65W charger $\rightarrow$ 100W multi-port desktop station, or earbuds $\rightarrow$ flagship ANC headphones).
  - Strictly respects explicit maximum budget constraints.
  - Generates clear, explainable reasons contrasting upgraded specifications and price differences.
- **Cross-sell Opportunities**:
  - Recommends complementary companion accessories (e.g. Keyboards $\rightarrow$ Ergonomic Mouse, Desk Mat, USB-C Hub; Backpack $\rightarrow$ Cable Organizer Pouch, Stainless Flask).
  - Deterministic relationship mapping across categories and functional roles.
- **Hard Constraints**:
  - Excludes inactive products (`is_active = False`).
  - Excludes out-of-stock products (`inventory <= 0`).
  - Excludes products exceeding explicitly defined max budget.
  - Excludes duplicates and never recommends the primary product as its own upsell/cross-sell.

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/agent/growth" \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me mechanical keyboards"}'
```

**Example Response:**
```json
{
  "message": "I found suitable products and 3 useful upgrade and accessory options.",
  "intent": {
    "intent": "product_search",
    "search_query": "mechanical keyboard",
    "category": "Computer Accessories",
    "min_price": null,
    "max_price": null,
    "currency": "INR",
    "availability_required": true
  },
  "primary_products": [
    {
      "id": "2eb0746e-1d37-4d92-bb8f-e18e77519ea8",
      "name": "ErgoPro Mechanical Wireless Keyboard",
      "category": "Computer Accessories",
      "price": "7999.00",
      "inventory": 35,
      "sku": "ACC-EP-KB01",
      "is_active": true
    }
  ],
  "upsell": [],
  "cross_sell": [
    {
      "type": "cross_sell",
      "product": {
        "id": "e2a0f8bf-1044-4861-bb38-5f5647587efc",
        "name": "PrecisionGlide Ergonomic Wireless Mouse",
        "category": "Computer Accessories",
        "price": "2499.00",
        "inventory": 90,
        "sku": "ACC-PG-MS02"
      },
      "primary_product_id": "2eb0746e-1d37-4d92-bb8f-e18e77519ea8",
      "primary_product_name": "ErgoPro Mechanical Wireless Keyboard",
      "score": 0.92,
      "reason": "An ergonomic wireless mouse is the ideal productivity companion to pair with your ErgoPro Mechanical Wireless Keyboard."
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10
}
```

### 3. Product Discovery Endpoints

#### `GET /api/products`
List active products with filtering, search, and pagination.

#### `GET /api/products/{product_id}`
Retrieve full product details by UUID. Returns `404 Not Found` if the product does not exist.

---

## Interactive Documentation

- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Interactive ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
