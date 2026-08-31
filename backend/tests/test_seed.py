from decimal import Decimal
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.core.database import Base
from app.core.seed import CATALOG_PRODUCTS, DEMO_MERCHANT_NAME, seed_catalog
from app.models import Merchant, Product


def get_test_db_session() -> Session:
    """Create an isolated in-memory SQLite database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_seed_creates_merchant_and_products():
    """Verify demo merchant and all products are created on initial run."""
    session = get_test_db_session()
    result = seed_catalog(session)

    assert result["merchant_name"] == DEMO_MERCHANT_NAME
    assert result["merchant_created"] is True
    assert result["products_created"] == len(CATALOG_PRODUCTS)
    assert result["total_products"] == len(CATALOG_PRODUCTS)
    assert result["total_products"] >= 12  # Ensure meets 12-15 requirement


def test_seed_idempotency_run_twice():
    """Verify executing the seed multiple times produces zero duplicates."""
    session = get_test_db_session()

    # First run
    result1 = seed_catalog(session)
    assert result1["merchant_created"] is True
    assert result1["products_created"] == len(CATALOG_PRODUCTS)

    # Second run
    result2 = seed_catalog(session)
    assert result2["merchant_created"] is False
    assert result2["products_created"] == 0
    assert result2["products_updated"] == len(CATALOG_PRODUCTS)
    assert result2["total_products"] == len(CATALOG_PRODUCTS)

    # Verify merchant count in database is exactly 1
    merchants = session.execute(select(Merchant)).scalars().all()
    assert len(merchants) == 1

    # Verify product count in database is unchanged
    products = session.execute(select(Product)).scalars().all()
    assert len(products) == len(CATALOG_PRODUCTS)


def test_seeded_products_attributes_and_relationships():
    """Verify field constraints, attribute validity, and merchant ownership."""
    session = get_test_db_session()
    seed_catalog(session)

    merchant = session.execute(select(Merchant).where(Merchant.name == DEMO_MERCHANT_NAME)).scalar_one()
    products = session.execute(select(Product).where(Product.merchant_id == merchant.id)).scalars().all()

    assert len(products) == len(CATALOG_PRODUCTS)

    skus = set()
    for product in products:
        # Belongs to correct merchant
        assert product.merchant_id == merchant.id
        assert product.merchant == merchant

        # SKU uniqueness
        assert product.sku not in skus
        skus.add(product.sku)

        # Price is non-negative and valid Decimal
        assert product.price >= Decimal("0.00")
        assert product.currency == "INR"

        # Inventory is strictly positive for active demo products
        assert product.inventory > 0
        assert product.is_active is True

        # Attributes are non-empty dicts containing structured metadata
        assert isinstance(product.attributes, dict)
        assert "brand" in product.attributes
        assert "tier" in product.attributes or "category" in product.__dict__


def test_catalog_category_distribution():
    """Verify catalog spans realistic related categories for upselling & cross-selling."""
    categories = {p["category"] for p in CATALOG_PRODUCTS}
    assert "Audio" in categories
    assert "Computer Accessories" in categories
    assert "Chargers & Cables" in categories
    assert "Work & Travel" in categories
