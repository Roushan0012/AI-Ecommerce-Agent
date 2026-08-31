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
from app.services.recommendation_service import recommendation_service


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


def test_recommend_endpoint_success(client):
    """Verify POST /api/agent/recommend returns 200 and ranked list."""
    response = client.post(
        "/api/agent/recommend",
        json={"message": "I need wireless headphones under ₹5000 for travelling"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "intent" in data
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert data["items"][0]["score"] > 0.0
    assert "reason" in data["items"][0]
    assert "product" in data["items"][0]


def test_recommend_ranking_order(client):
    """Verify recommended items are sorted strictly in descending score order."""
    response = client.post(
        "/api/agent/recommend",
        json={"message": "Show me fast chargers between 1000 and 4000"},
    )
    assert response.status_code == 200
    data = response.json()
    items = data["items"]
    assert len(items) >= 2

    # Check non-increasing score order
    scores = [it["score"] for it in items]
    assert scores == sorted(scores, reverse=True)


def test_recommend_category_matching(client):
    """Verify recommendations strictly match or prioritize queried category."""
    response = client.post(
        "/api/agent/recommend",
        json={"message": "I want something for travel"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"]["category"] == "Work & Travel"
    assert data["total"] == 3
    for it in data["items"]:
        assert it["product"]["category"] == "Work & Travel"
        assert "Matches category 'Work & Travel'" in it["reason"]


def test_recommend_keyword_relevance(client):
    """Verify specific keyword in prompt ranks matching item higher."""
    response = client.post(
        "/api/agent/recommend",
        json={"message": "I need a mechanical keyboard"},
    )
    assert response.status_code == 200
    top_item = response.json()["items"][0]
    assert "Mechanical" in top_item["product"]["name"]
    assert "mechanical" in top_item["reason"].lower() or "keyboard" in top_item["reason"].lower()


def test_recommend_hard_budget_constraint(client):
    """Verify items exceeding max_price are strictly excluded."""
    response = client.post(
        "/api/agent/recommend",
        json={"message": "I need headphones under ₹5000"},
    )
    assert response.status_code == 200
    data = response.json()
    for it in data["items"]:
        assert Decimal(it["product"]["price"]) <= Decimal("5000.00")
        # AuraPulse (₹14,999) must NOT be present
        assert it["product"]["name"] != "AuraPulse Wireless Noise-Cancelling Headphones"


def test_recommend_availability_filtering(client):
    """Verify all recommended products are active and in stock."""
    response = client.post(
        "/api/agent/recommend",
        json={"message": "Show me accessories"},
    )
    assert response.status_code == 200
    for it in response.json()["items"]:
        assert it["product"]["is_active"] is True
        assert it["product"]["inventory"] > 0
        assert "available in stock" in it["reason"]


def test_recommend_combined_constraints(client):
    """Verify combined category, price range, and availability constraints."""
    response = client.post(
        "/api/agent/recommend",
        json={"message": "Find computer accessories between ₹1000 and ₹3000"},
    )
    assert response.status_code == 200
    data = response.json()
    for it in data["items"]:
        assert it["product"]["category"] == "Computer Accessories"
        assert Decimal("1000.00") <= Decimal(it["product"]["price"]) <= Decimal("3000.00")


def test_recommend_no_results(client):
    """Verify impossible budget or query returns 0 recommendations with clear message."""
    response = client.post(
        "/api/agent/recommend",
        json={"message": "I want a laptop stand under ₹50"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert "No recommended products found" in data["message"]


def test_recommend_non_shopping_intent(client):
    """Verify conversational / general greetings return 0 items and polite message."""
    response = client.post(
        "/api/agent/recommend",
        json={"message": "Hi, who created you?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"]["intent"] == "general"
    assert data["total"] == 0
    assert data["items"] == []


def test_recommend_empty_message_validation(client):
    """Verify empty message returns HTTP 422."""
    resp = client.post("/api/agent/recommend", json={"message": ""})
    assert resp.status_code == 422


def test_recommend_unit_scoring_logic():
    """Unit test individual score_product function on dummy product."""
    from uuid import uuid4
    prod = ProductResponse(
        id=uuid4(),
        merchant_id=uuid4(),
        name="Ultra ANC Headphones",
        description="Premium active noise cancelling travel headphones",
        category="Audio",
        price=Decimal("4999.00"),
        currency="INR",
        inventory=50,
        sku="TEST-SKU-01",
        attributes={"brand": "Aura", "feature": "ANC"},
        is_active=True,
        created_at="2026-09-01T00:00:00Z",
        updated_at="2026-09-01T00:00:00Z",
    )

    intent = ShoppingIntent(
        intent="product_search",
        category="Audio",
        search_query="headphones",
        max_price=Decimal("6000.00"),
        availability_required=True,
    )

    score, reason = recommendation_service.score_product(prod, intent, "travel headphones under 6000")
    assert score > 0.6
    assert "Matches category 'Audio'" in reason
    assert "in stock" in reason

    # Out of stock test
    prod_oos = prod.model_copy(update={"inventory": 0})
    score_oos, reason_oos = recommendation_service.score_product(prod_oos, intent, "travel headphones")
    assert score_oos == 0.0
    assert "out of stock" in reason_oos.lower()

    # Over budget test
    intent_low_budget = intent.model_copy(update={"max_price": Decimal("3000.00")})
    score_over, reason_over = recommendation_service.score_product(prod, intent_low_budget, "cheap headphones")
    assert score_over == 0.0
    assert "exceeds max budget" in reason_over.lower()
