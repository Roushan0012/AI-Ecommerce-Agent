# Database Architecture and Schema

## 1. Overview

The AI Commerce Agent Platform persists state in a PostgreSQL relational database hosted on Supabase and managed through the SQLAlchemy 2.0 ORM. The relational model enforces referential integrity through foreign key cascades, database-level check constraints, unique constraints, and optimized index layouts.

Database schema versioning is managed via Alembic migrations located in `backend/alembic/`. Migration scripts ensure that tables, columns, indexes, and constraints can be reproduced deterministically across local, test, and production environments.

---

## 2. Entity Relationship Diagram

```
+------------------+             +------------------+
|      users       |             |    merchants     |
+------------------+             +------------------+
| id (PK)          |             | id (PK)          |
| email            |             | name             |
| password_hash    |             | description      |
| role             |             | created_at       |
| is_active        |             | updated_at       |
| created_at       |             +--------+---------+
| updated_at       |                      | 1
+------------------+                      |
                                          | has many
                                          v *
+------------------+             +------------------+
|      carts       |             |     products     |
+------------------+             +------------------+
| id (PK)          |             | id (PK)          |
| customer_id (FK) |             | merchant_id (FK) |
| status           |             | name             |
| currency         |             | description      |
| subtotal         |             | category         |
| discount         |             | price            |
| total            |             | currency         |
| created_at       |             | inventory        |
| updated_at       |             | sku              |
+--------+---------+             | attributes JSONB |
         | 1                     | is_active        |
         | has many              | image_url        |
         v *                     | created_at       |
+------------------+             | updated_at       |
|    cart_items    |             +--------+---------+
+------------------+                      | 1
| id (PK)          |                      |
| cart_id (FK)     |<---------------------+ has many (in cart/order)
| product_id (FK)  |                      |
| quantity         |                      v *
| unit_price       |             +------------------+
| total_price      |             |   order_items    |
| created_at       |             +------------------+
| updated_at       |             | id (PK)          |
+------------------+             | order_id (FK)    |
                                 | product_id (FK)  |
+------------------+             | product_name     |
|      orders      |             | sku              |
+------------------+             | quantity         |
| id (PK)          |             | unit_price       |
| merchant_id (FK) |             | total_price      |
| customer_id (FK) |             | created_at       |
| cart_id (FK)     |             +------------------+
| status           |                      ^ *
| currency         |                      | has many
| subtotal         |                      | 1
| discount         |             +--------+---------+
| total            |             |      orders      |
| razorpay_order_id|             +--------+---------+
| created_at       |                      | 1
| updated_at       |                      | has many
+--------+---------+                      v *
         |                       +------------------+
         +---------------------->|     payments     |
                                 +------------------+
                                 | id (PK)          |
                                 | order_id (FK)    |
                                 | razorpay_order_id|
+------------------+             | razorpay_pay_id  |
|    audit_logs    |             | amount           |
+------------------+             | currency         |
| id (PK)          |             | status           |
| customer_id      |             | created_at       |
| session_id       |             | updated_at       |
| event_type       |             +------------------+
| action           |
| payload JSON     |
| result JSON      |
| status           |
| error_message    |
| cart_id          |
| order_id         |
| payment_id       |
| created_at       |
+------------------+
```

---

## 3. Table Definitions and Specifications

### 3.1 `users` Table
Stores registered customer, merchant, and administrative accounts.

| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `uuid.uuid4()` | Primary Key | Unique user identifier |
| `email` | `VARCHAR(255)` | No | None | Unique, Index | User email address used for authentication |
| `password_hash` | `VARCHAR(255)` | No | None | | Argon2id password hash |
| `role` | `VARCHAR(50)` | No | `'customer'` | Index | Role identifier: `'customer'`, `'merchant'`, `'admin'` |
| `is_active` | `BOOLEAN` | No | `True` | | Account status flag |
| `created_at` | `TIMESTAMPTZ` | No | UTC Now | | Timestamp of account creation |
| `updated_at` | `TIMESTAMPTZ` | No | UTC Now | On update: UTC Now | Timestamp of last account modification |

- **Business Rules**:
  - The `role` column is validated by a SQLAlchemy validator (`validate_role`) ensuring values belong strictly to `UserRole.values()` (`customer`, `merchant`, `admin`).
  - Public registration defaults to `customer`. Role elevation cannot be requested through registration payloads.

---

### 3.2 `merchants` Table
Represents store operators and merchant entities that own products and fulfill orders.

| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `uuid.uuid4()` | Primary Key | Unique merchant identifier |
| `name` | `VARCHAR(255)` | No | None | | Legal business or store name |
| `description` | `TEXT` | Yes | None | | Public store profile description |
| `created_at` | `TIMESTAMPTZ` | No | UTC Now | | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | UTC Now | On update: UTC Now | Last modification timestamp |

- **Relationships**:
  - `products`: One-to-many relationship with `Product` (cascade on delete).
  - `orders`: One-to-many relationship with `Order` (cascade on delete).

---

### 3.3 `products` Table
Stores catalog merchandise items, inventory counts, pricing, and technical attributes.

| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `uuid.uuid4()` | Primary Key | Product UUID |
| `merchant_id` | `UUID` | No | None | Foreign Key (`merchants.id`), Index | Merchant that owns and supplies the product |
| `name` | `VARCHAR(255)` | No | None | | Product name / title |
| `description` | `TEXT` | Yes | None | | Detailed description |
| `category` | `VARCHAR(100)` | Yes | None | Index | Primary category (`Audio`, `Computer Accessories`, etc.) |
| `price` | `NUMERIC(12, 2)` | No | None | Check (`price >= 0`) | Authoritative unit price |
| `currency` | `VARCHAR(3)` | No | `'INR'` | | Three-letter currency code |
| `inventory` | `INTEGER` | No | `0` | Check (`inventory >= 0`) | Available physical stock quantity |
| `sku` | `VARCHAR(100)` | No | None | | Merchant Stock Keeping Unit identifier |
| `attributes` | `JSONB` | No | `{}` | | Key-value technical specifications (driver size, ANC, etc.) |
| `is_active` | `BOOLEAN` | No | `True` | Index | Catalog visibility toggle |
| `image_url` | `TEXT` | Yes | None | | URL link to product preview image |
| `created_at` | `TIMESTAMPTZ` | No | UTC Now | | Product creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | UTC Now | On update: UTC Now | Product update timestamp |

- **Constraints**:
  - `uq_products_merchant_sku`: Unique constraint on `(merchant_id, sku)`.
  - `chk_products_price_non_negative`: Ensures `price >= 0`.
  - `chk_products_inventory_non_negative`: Ensures `inventory >= 0`.

---

### 3.4 `carts` Table
Maintains persistent shopping carts for authenticated customers.

| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `uuid.uuid4()` | Primary Key | Cart UUID |
| `customer_id` | `UUID` | No | None | Index | Owner customer UUID |
| `status` | `VARCHAR(50)` | No | `'active'` | Index | Cart state (`'active'`, `'converted'`, `'abandoned'`) |
| `currency` | `VARCHAR(3)` | No | `'INR'` | | Cart currency code |
| `subtotal` | `NUMERIC(12, 2)` | No | `0.00` | Check (`subtotal >= 0`) | Sum of item totals calculated server-side |
| `discount` | `NUMERIC(12, 2)` | No | `0.00` | Check (`discount >= 0`) | Total discount calculated server-side |
| `total` | `NUMERIC(12, 2)` | No | `0.00` | Check (`total >= 0`) | Final payable balance (`subtotal - discount`) |
| `created_at` | `TIMESTAMPTZ` | No | UTC Now | | Cart creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | UTC Now | On update: UTC Now | Cart update timestamp |

- **Business Rules**:
  - A customer can only have one active cart at any time. Adding items to a cart queries for `status == 'active'`.
  - When an order is created from a cart, `cart.status` transitions from `'active'` to `'converted'`.

---

### 3.5 `cart_items` Table
Stores individual product line items within an active or converted cart.

| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `uuid.uuid4()` | Primary Key | Cart item UUID |
| `cart_id` | `UUID` | No | None | Foreign Key (`carts.id`), Index | Parent cart reference |
| `product_id` | `UUID` | No | None | Foreign Key (`products.id`), Index | Selected catalog product |
| `quantity` | `INTEGER` | No | `1` | Check (`quantity > 0`) | Number of units requested |
| `unit_price` | `NUMERIC(12, 2)` | No | None | Check (`unit_price >= 0`) | Authoritative unit price at time of addition |
| `total_price` | `NUMERIC(12, 2)` | No | None | Check (`total_price >= 0`) | Line total (`quantity * unit_price`) |
| `created_at` | `TIMESTAMPTZ` | No | UTC Now | | Item creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | UTC Now | On update: UTC Now | Item update timestamp |

- **Constraints**:
  - `uq_cart_items_cart_product`: Unique constraint ensuring a product appears at most once per cart. Repeated additions increment `quantity` rather than inserting duplicate records.
  - Foreign key on `cart_id` cascades on delete (`ondelete="CASCADE"`).
  - Foreign key on `product_id` cascades on delete (`ondelete="CASCADE"`).

---

### 3.6 `orders` Table
Represents authoritative commercial purchase commitments and their execution states.

| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `uuid.uuid4()` | Primary Key | Order UUID |
| `merchant_id` | `UUID` | No | None | Foreign Key (`merchants.id`), Index | Merchant fulfilling the order |
| `customer_id` | `UUID` | No | None | Index | Purchasing customer UUID |
| `cart_id` | `UUID` | Yes | None | Foreign Key (`carts.id`), Index | Converted cart reference (null on cart delete) |
| `status` | `VARCHAR(50)` | No | `'pending_payment'` | Index | Order state machine lifecycle status |
| `currency` | `VARCHAR(3)` | No | `'INR'` | | Order currency |
| `subtotal` | `NUMERIC(12, 2)` | No | `0.00` | Check (`subtotal >= 0`) | Server-calculated subtotal |
| `discount` | `NUMERIC(12, 2)` | No | `0.00` | Check (`discount >= 0`) | Applied discount |
| `total` | `NUMERIC(12, 2)` | No | `0.00` | Check (`total >= 0`) | Final payable order balance |
| `razorpay_order_id` | `VARCHAR(255)` | Yes | None | Unique, Index | External Razorpay order reference |
| `created_at` | `TIMESTAMPTZ` | No | UTC Now | | Order creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | UTC Now | On update: UTC Now | Order status update timestamp |

- **Order Status Values**:
  - `pending_payment`: Order created, stock verified, awaiting payment authorization.
  - `paid`: Payment verified cryptographically via Razorpay callback or webhook.
  - `payment_failed`: Payment was declined or cancelled.
  - `cancelled`: Order cancelled prior to delivery; triggers stock restock.

---

### 3.7 `order_items` Table
Stores immutable snapshots of products purchased in an order.

| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `uuid.uuid4()` | Primary Key | Order item UUID |
| `order_id` | `UUID` | No | None | Foreign Key (`orders.id`), Index | Parent order reference (cascades on delete) |
| `product_id` | `UUID` | No | None | Foreign Key (`products.id`), Index | Referenced product (`ondelete="RESTRICT"`) |
| `product_name` | `VARCHAR(255)` | No | None | | Immutable snapshot of product name at purchase |
| `sku` | `VARCHAR(100)` | No | None | | Immutable snapshot of product SKU at purchase |
| `quantity` | `INTEGER` | No | None | Check (`quantity > 0`) | Quantity purchased |
| `unit_price` | `NUMERIC(12, 2)` | No | None | Check (`unit_price >= 0`) | Immutable unit price snapshot |
| `total_price` | `NUMERIC(12, 2)` | No | None | Check (`total_price >= 0`) | Line total snapshot (`quantity * unit_price`) |
| `created_at` | `TIMESTAMPTZ` | No | UTC Now | | Creation timestamp |

- **Immutability Principle**: `product_name`, `sku`, and `unit_price` are captured at the moment of order creation. Future updates to the product catalog do not mutate historical order records.

---

### 3.8 `payments` Table
Records payment transaction attempts and confirmations linked to orders.

| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `uuid.uuid4()` | Primary Key | Payment attempt UUID |
| `order_id` | `UUID` | No | None | Foreign Key (`orders.id`), Index | Associated order reference |
| `razorpay_order_id` | `VARCHAR(255)` | No | None | Index | Razorpay order reference (`order_*`) |
| `razorpay_payment_id` | `VARCHAR(255)` | Yes | None | Index | Razorpay payment authorization ID (`pay_*`) |
| `amount` | `NUMERIC(12, 2)` | No | `0.00` | Check (`amount >= 0`) | Authoritative payable amount |
| `currency` | `VARCHAR(3)` | No | `'INR'` | | Currency code |
| `status` | `VARCHAR(50)` | No | `'created'` | Index | Status: `'created'`, `'paid'`, `'failed'` |
| `created_at` | `TIMESTAMPTZ` | No | UTC Now | | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | UTC Now | On update: UTC Now | Status update timestamp |

---

### 3.9 `audit_logs` Table
Provides an append-only forensic audit trail recording events across agents, shoppers, orders, and payments.

| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `uuid.uuid4()` | Primary Key | Audit entry UUID |
| `customer_id` | `UUID` | Yes | None | Index | Associated user UUID if authenticated |
| `session_id` | `VARCHAR(255)` | Yes | None | Index | Client or agent session identifier |
| `event_type` | `VARCHAR(100)` | No | None | Index | Event category (e.g., `USER_REQUEST`, `PAYMENT_EVENT`) |
| `action` | `VARCHAR(255)` | Yes | None | Index | Action name (e.g., `create_order`, `add_item_to_cart`) |
| `payload` | `JSON` | Yes | None | | Sanitized request payload |
| `result` | `JSON` | Yes | None | | Sanitized operation result |
| `status` | `VARCHAR(50)` | No | `'success'` | Index | Execution outcome (`'success'`, `'failed'`, `'rejected'`) |
| `error_message` | `TEXT` | Yes | None | | Error message if failed |
| `cart_id` | `UUID` | Yes | None | Index | Associated cart UUID |
| `order_id` | `UUID` | Yes | None | Index | Associated order UUID |
| `payment_id` | `UUID` | Yes | None | Index | Associated payment UUID |
| `created_at` | `TIMESTAMPTZ` | No | UTC Now | Index | UTC timestamp of event execution |
