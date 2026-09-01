"""Database migration runner for AI Commerce Agent platform."""

import logging
from sqlalchemy import text
from app.core.database import Base, get_engine
import app.models  # Ensures all models are registered with Base.metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

POSTGRES_MIGRATION_STATEMENTS = [
    # 1. Create carts table
    (
        "Create carts table",
        """
        CREATE TABLE IF NOT EXISTS carts (
            id UUID PRIMARY KEY,
            customer_id UUID NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'active',
            currency VARCHAR(3) NOT NULL DEFAULT 'INR',
            subtotal NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
            discount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
            total NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_carts_subtotal_non_negative CHECK (subtotal >= 0),
            CONSTRAINT chk_carts_discount_non_negative CHECK (discount >= 0),
            CONSTRAINT chk_carts_total_non_negative CHECK (total >= 0)
        )
        """,
    ),
    (
        "Create index ix_carts_customer_id",
        "CREATE INDEX IF NOT EXISTS ix_carts_customer_id ON carts(customer_id)",
    ),
    (
        "Create index ix_carts_status",
        "CREATE INDEX IF NOT EXISTS ix_carts_status ON carts(status)",
    ),
    # 2. Create cart_items table
    (
        "Create cart_items table",
        """
        CREATE TABLE IF NOT EXISTS cart_items (
            id UUID PRIMARY KEY,
            cart_id UUID NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
            product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price NUMERIC(12, 2) NOT NULL,
            total_price NUMERIC(12, 2) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_cart_items_cart_product UNIQUE (cart_id, product_id),
            CONSTRAINT chk_cart_items_quantity_positive CHECK (quantity > 0),
            CONSTRAINT chk_cart_items_unit_price_non_negative CHECK (unit_price >= 0),
            CONSTRAINT chk_cart_items_total_price_non_negative CHECK (total_price >= 0)
        )
        """,
    ),
    (
        "Create index ix_cart_items_cart_id",
        "CREATE INDEX IF NOT EXISTS ix_cart_items_cart_id ON cart_items(cart_id)",
    ),
    (
        "Create index ix_cart_items_product_id",
        "CREATE INDEX IF NOT EXISTS ix_cart_items_product_id ON cart_items(product_id)",
    ),
    # 3. Add missing columns / indexes to orders
    (
        "Add customer_id to orders",
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_id UUID",
    ),
    (
        "Add cart_id to orders",
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS cart_id UUID REFERENCES carts(id) ON DELETE SET NULL",
    ),
    (
        "Add discount to orders",
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS discount NUMERIC(12, 2) NOT NULL DEFAULT 0.00",
    ),
    (
        "Create index ix_orders_customer_id",
        "CREATE INDEX IF NOT EXISTS ix_orders_customer_id ON orders(customer_id)",
    ),
    (
        "Create index ix_orders_cart_id",
        "CREATE INDEX IF NOT EXISTS ix_orders_cart_id ON orders(cart_id)",
    ),
    # 4. Add missing snapshot columns to order_items
    (
        "Add product_name to order_items",
        "ALTER TABLE order_items ADD COLUMN IF NOT EXISTS product_name VARCHAR(255)",
    ),
    (
        "Add sku to order_items",
        "ALTER TABLE order_items ADD COLUMN IF NOT EXISTS sku VARCHAR(100)",
    ),
    # 5. Create payments table (Step 2.10)
    (
        "Create payments table",
        """
        CREATE TABLE IF NOT EXISTS payments (
            id UUID PRIMARY KEY,
            order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            razorpay_order_id VARCHAR(255) NOT NULL,
            razorpay_payment_id VARCHAR(255),
            amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
            currency VARCHAR(3) NOT NULL DEFAULT 'INR',
            status VARCHAR(50) NOT NULL DEFAULT 'created',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_payments_amount_non_negative CHECK (amount >= 0)
        )
        """,
    ),
    (
        "Create index ix_payments_order_id",
        "CREATE INDEX IF NOT EXISTS ix_payments_order_id ON payments(order_id)",
    ),
    (
        "Create index ix_payments_razorpay_order_id",
        "CREATE INDEX IF NOT EXISTS ix_payments_razorpay_order_id ON payments(razorpay_order_id)",
    ),
    (
        "Create index ix_payments_status",
        "CREATE INDEX IF NOT EXISTS ix_payments_status ON payments(status)",
    ),
]


def run_migrations(engine=None) -> None:
    """
    Safely and idempotently executes schema migrations across PostgreSQL or SQLite databases.
    """
    if engine is None:
        engine = get_engine()

    dialect_name = engine.dialect.name
    logger.info(f"Running migrations for dialect: {dialect_name}")

    if dialect_name == "postgresql":
        try:
            with engine.connect() as conn:
                for desc, stmt in POSTGRES_MIGRATION_STATEMENTS:
                    logger.info(f"Applying: {desc}")
                    conn.execute(text(stmt))
                    conn.commit()
            logger.info("PostgreSQL schema migrations applied successfully.")
        except Exception as e:
            logger.warning(f"Direct PostgreSQL migration connection skipped/failed: {e}")
            Base.metadata.create_all(engine)
            logger.info("Declarative metadata tables verified.")
    else:
        # SQLite fallback for local test suite
        Base.metadata.create_all(engine)
        logger.info("SQLite schema tables created successfully.")


if __name__ == "__main__":
    run_migrations()
