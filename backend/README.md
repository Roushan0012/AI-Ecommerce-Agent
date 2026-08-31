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
│   │   └── product.py
│   ├── services/
│   │   └── ai_agent.py
│   └── main.py
├── tests/
│   ├── test_agent_api.py
│   ├── test_database_health.py
│   ├── test_health.py
│   ├── test_models.py
│   ├── test_products_api.py
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

### 2. AI Agent Endpoint

#### `POST /api/agent/understand`
Converts customer natural language shopping requests into structured shopping intent.

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/agent/understand" \
  -H "Content-Type: application/json" \
  -d '{"message": "I need wireless headphones under ₹5000"}'
```

**Example Response:**
```json
{
  "message": "I found options matching 'wireless headphones' in Audio under ₹5,000.",
  "intent": {
    "intent": "product_search",
    "search_query": "wireless headphones",
    "category": "Audio",
    "min_price": null,
    "max_price": "5000.0",
    "currency": "INR",
    "availability_required": true
  }
}
```

### 3. Product Discovery Endpoints

#### `GET /api/products`
List active products with filtering, search, and pagination.

**Query Parameters:**
| Parameter | Type | Default | Description |
|---|---|---|---|
| `search` | `string` | `null` | Keyword search against name & description |
| `category` | `string` | `null` | Filter by category (e.g. `Audio`, `Computer Accessories`) |
| `min_price` | `decimal` | `null` | Minimum price filter (INR) |
| `max_price` | `decimal` | `null` | Maximum price filter (INR) |
| `available` | `boolean` | `null` | When `true`, returns only in-stock active items (`inventory > 0`) |
| `page` | `integer` | `1` | Page number (1-indexed, `ge=1`) |
| `page_size` | `integer` | `10` | Number of items per page (`1 <= page_size <= 100`) |

**Example Request:**
```bash
curl "http://localhost:8000/api/products?category=Audio&min_price=2000&max_price=15000&page=1&page_size=5"
```

#### `GET /api/products/{product_id}`
Retrieve full product details by UUID. Returns `404 Not Found` if the product does not exist.

---

## Interactive Documentation

- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Interactive ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
