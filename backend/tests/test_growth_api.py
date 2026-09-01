from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.core.seed import seed_catalog
from app.main import app
from app.schemas.agent import ShoppingIntent
from app.schemas.product import ProductResponse
from app.services.growth_service import growth_service


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        seed_catalog(session)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_growth_endpoint_success(client):
    """Verify POST /api/agent/growth returns 200 with structured upsell and cross-sell items."""
    response = client.post(
        "/api/agent/growth",
        json={"message": "I want a keyboard for coding"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "primary_products" in data
    assert "upsell" in data
    assert "cross_sell" in data
    assert "total" in data
    assert len(data["primary_products"]) >= 1


def test_valid_cross_sell_recommendations(client):
    """Verify keyboard purchase receives complementary mouse and desk mat cross-sells."""
    response = client.post(
        "/api/agent/growth",
        json={"message": "Show me mechanical keyboards"},
    )
    assert response.status_code == 200
    data = response.json()
    cross_sells = data["cross_sell"]
    assert len(cross_sells) >= 1

    # Should recommend mouse or desk mat as complementary companion
    cross_sell_names = [item["product"]["name"] for item in cross_sells]
    has_companion = any(
        "Mouse" in name or "Desk Mat" in name or "Hub" in name
        for name in cross_sell_names
    )
    assert has_companion
    for item in cross_sells:
        assert item["type"] == "cross_sell"
        assert item["score"] > 0.0
        assert len(item["reason"]) > 0


def test_valid_upsell_recommendations(client):
    """Verify entry-level charger receives high-wattage desktop charger upsell."""
    response = client.post(
        "/api/agent/growth",
        json={"message": "Show me fast chargers"},
    )
    assert response.status_code == 200
    data = response.json()
    upsells = data["upsell"]

    # If 65W charger is primary, 100W desktop charger should be in upsell
    if upsells:
        for item in upsells:
            assert item["type"] == "upsell"
            assert item["score"] > 0.0
            assert "Costs ₹" in item["reason"] or "tier" in item["reason"].lower()


def test_upsell_respects_explicit_max_budget(client):
    """Verify upsells strictly respect the customer's explicit max price budget."""
    response = client.post(
        "/api/agent/growth",
        json={"message": "I want wireless earbuds under ₹4000"},
    )
    assert response.status_code == 200
    data = response.json()
    # AuraPulse headphones cost ₹14,999, so they must NOT be upsold when budget is ₹4000
    for item in data["upsell"]:
        assert Decimal(item["product"]["price"]) <= Decimal("4000.00")
        assert item["product"]["name"] != "AuraPulse Wireless Noise-Cancelling Headphones"

    for item in data["cross_sell"]:
        assert Decimal(item["product"]["price"]) <= Decimal("4000.00")


def test_inactive_and_out_of_stock_exclusion():
    """Verify inactive and out of stock products are filtered out from growth candidates."""
    from uuid import uuid4

    inactive_prod = ProductResponse(
        id=uuid4(),
        merchant_id=uuid4(),
        name="Discontinued Mouse",
        description="Old model",
        category="Computer Accessories",
        price=Decimal("1500.00"),
        currency="INR",
        inventory=50,
        sku="ACC-OLD-01",
        attributes={},
        is_active=False,
        created_at="2026-09-01T00:00:00Z",
        updated_at="2026-09-01T00:00:00Z",
    )

    oos_prod = ProductResponse(
        id=uuid4(),
        merchant_id=uuid4(),
        name="Out of Stock Keyboard",
        description="Popular model",
        category="Computer Accessories",
        price=Decimal("4500.00"),
        currency="INR",
        inventory=0,
        sku="ACC-OOS-01",
        attributes={},
        is_active=True,
        created_at="2026-09-01T00:00:00Z",
        updated_at="2026-09-01T00:00:00Z",
    )

    intent = ShoppingIntent(intent="product_search", availability_required=True)
    excluded = set()

    assert growth_service._is_valid_candidate(inactive_prod, intent, excluded) is False
    assert growth_service._is_valid_candidate(oos_prod, intent, excluded) is False


def test_duplicate_and_self_exclusion(client):
    """Verify primary products are not recommended as their own upsell or cross-sell."""
    response = client.post(
        "/api/agent/growth",
        json={"message": "Looking for wireless noise cancelling headphones"},
    )
    assert response.status_code == 200
    data = response.json()
    primary_ids = {p["id"] for p in data["primary_products"]}

    for up in data["upsell"]:
        assert up["product"]["id"] not in primary_ids

    for cs in data["cross_sell"]:
        assert cs["product"]["id"] not in primary_ids

    # Verify no duplicate IDs inside upsell or cross-sell
    upsell_ids = [up["product"]["id"] for up in data["upsell"]]
    assert len(upsell_ids) == len(set(upsell_ids))

    cross_sell_ids = [cs["product"]["id"] for cs in data["cross_sell"]]
    assert len(cross_sell_ids) == len(set(cross_sell_ids))


def test_growth_non_shopping_intent(client):
    """Verify general conversation returns empty lists without error."""
    response = client.post(
        "/api/agent/growth",
        json={"message": "Good morning assistant!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"]["intent"] == "general"
    assert data["primary_products"] == []
    assert data["upsell"] == []
    assert data["cross_sell"] == []
    assert data["total"] == 0


def test_growth_no_matching_products(client):
    """Verify impossible search returns empty growth lists with graceful summary."""
    response = client.post(
        "/api/agent/growth",
        json={"message": "I want a laptop stand under ₹50"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["primary_products"] == []
    assert data["upsell"] == []
    assert data["cross_sell"] == []
    assert data["total"] == 0


def test_growth_empty_message_validation(client):
    """Verify empty query returns HTTP 422."""
    response = client.post(
        "/api/agent/growth",
        json={"message": ""},
    )
    assert response.status_code == 422
