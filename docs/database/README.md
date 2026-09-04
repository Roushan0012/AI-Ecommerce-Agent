# Database Schema & Migrations

This directory contains the database migration scripts, catalog seed files, and schema definitions for the AI Commerce Agent platform (Supabase PostgreSQL).

## Schema Overview

### 1. `merchants`
Stores merchant tenant profiles.
- `id` (UUID, Primary Key)
- `name` (VARCHAR, Required)
- `description` (TEXT, Optional)
- `created_at`, `updated_at` (TIMESTAMPTZ)

### 2. `products`
Stores product catalog per merchant.
- `id` (UUID, Primary Key)
- `merchant_id` (UUID, Foreign Key → `merchants.id`)
- `name` (VARCHAR, Required)
- `description` (TEXT, Optional)
- `category` (VARCHAR, Indexed)
- `price` (NUMERIC(12,2), Non-negative Check Constraint)
- `currency` (VARCHAR(3), Default 'INR')
- `inventory` (INTEGER, Non-negative Check Constraint)
- `sku` (VARCHAR, Unique per merchant via `(merchant_id, sku)`)
- `attributes` (JSONB, Default `{}`)
- `is_active` (BOOLEAN, Default true, Indexed)
- `created_at`, `updated_at` (TIMESTAMPTZ)

### 3. `orders`
Stores customer orders for a merchant.
- `id` (UUID, Primary Key)
- `merchant_id` (UUID, Foreign Key → `merchants.id`)
- `customer_id` (UUID, Nullable)
- `status` (VARCHAR(50), Default 'created', Indexed)
- `currency` (VARCHAR(3), Default 'INR')
- `subtotal` (NUMERIC(12,2), Non-negative Check Constraint)
- `total` (NUMERIC(12,2), Non-negative Check Constraint)
- `razorpay_order_id` (VARCHAR, Unique when present, Indexed)
- `created_at`, `updated_at` (TIMESTAMPTZ)

### 4. `order_items`
Stores line items within each order.
- `id` (UUID, Primary Key)
- `order_id` (UUID, Foreign Key → `orders.id`, Indexed)
- `product_id` (UUID, Foreign Key → `products.id`, Indexed)
- `quantity` (INTEGER, Positive Check Constraint `> 0`)
- `unit_price` (NUMERIC(12,2), Non-negative Check Constraint)
- `total_price` (NUMERIC(12,2), Non-negative Check Constraint)
- `created_at` (TIMESTAMPTZ)

---

## Migration & Seed Scripts

1. `001_initial_schema.sql`: Core schema creation with indexes, foreign keys, and check constraints.
2. `002_seed_products.sql`: Idempotent SQL script to seed the demo merchant (`AI Commerce Demo Store`) and 14 realistic products across Audio, Computer Accessories, Chargers & Cables, and Work & Travel categories.
3. `003_add_product_image_url.sql`: Idempotent SQL migration adding the nullable `image_url` column to `products`.

---

## Running Seeds & Migrations via Python

From `backend/`:
```bash
# Seed demo catalog
python -m app.core.seed
```
