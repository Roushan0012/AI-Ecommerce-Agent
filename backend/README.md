# AI Commerce Agent - Backend API

FastAPI backend service for the Razorpay AI Buildathon Track 01 "AI Commerce Agent".

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── products.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── seed.py
│   ├── models/
│   │   ├── merchant.py
│   │   ├── product.py
│   │   ├── order.py
│   │   └── order_item.py
│   ├── schemas/
│   │   └── product.py
│   ├── services/
│   └── main.py
├── tests/
│   ├── test_health.py
│   ├── test_database_health.py
│   ├── test_models.py
│   ├── test_seed.py
│   └── test_products_api.py
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

Copy `.env.example` to `.env` and fill in your Supabase connection parameters:

```bash
cp .env.example .env
```

Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string (e.g. `postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres`)
- `SUPABASE_URL`: Supabase project URL (optional for database connection probe)
- `SUPABASE_PUBLISHABLE_KEY`: Supabase anon/publishable key (optional for database connection probe)

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

### 2. Product Discovery Endpoints

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

**Example Response:**
```json
{
  "items": [
    {
      "id": "0d7df0d6-74ab-4242-81db-b87ea0ee89ac",
      "merchant_id": "6b583a79-0f19-483c-81da-cdf9f13aef71",
      "name": "SonicBoom Portable Bluetooth Speaker",
      "description": "Rugged 20W portable speaker delivering 360-degree bass-boosted sound...",
      "category": "Audio",
      "price": "2999.00",
      "currency": "INR",
      "inventory": 60,
      "sku": "AUD-SB-SP03",
      "attributes": {
        "brand": "SonicWave",
        "color": "Navy Blue",
        "output_power": "20W RMS"
      },
      "is_active": true,
      "created_at": "2026-08-31T20:31:17.325895Z",
      "updated_at": "2026-08-31T20:31:17.325901Z"
    }
  ],
  "total": 3,
  "page": 1,
  "page_size": 5
}
```

#### `GET /api/products/{product_id}`
Retrieve full product details by UUID. Returns `404 Not Found` if the product does not exist.

**Example Request:**
```bash
curl "http://localhost:8000/api/products/0d7df0d6-74ab-4242-81db-b87ea0ee89ac"
```

---

## Interactive Documentation

- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Interactive ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
