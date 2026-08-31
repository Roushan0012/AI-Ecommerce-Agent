# AI Commerce Agent - Backend API

FastAPI backend service for the Razorpay AI Buildathon Track 01 "AI Commerce Agent".

## Project Structure

```
backend/
├── app/
│   ├── api/
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
│   ├── services/
│   └── main.py
├── tests/
│   ├── test_health.py
│   ├── test_database_health.py
│   ├── test_models.py
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

## Endpoints & Documentation

- **Service Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- **Database Health Check**: [http://localhost:8000/api/health/database](http://localhost:8000/api/health/database)
- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Interactive ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
