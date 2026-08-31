from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.core.seed import seed_catalog
from app.main import app
from app.schemas.agent import (
    AgentSearchRequest,
    AgentSearchResponse,
    AgentUnderstandRequest,
    AgentUnderstandResponse,
    ShoppingIntent,
)
from app.services.ai_agent import (
    AIAgentService,
    AIConfigurationError,
    AIProviderError,
    BaseAIProvider,
    MockAIProvider,
)


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


# === Understand Intent Tests ===

def test_valid_shopping_message_accepted(client):
    """Verify valid natural language shopping message returns 200 and valid schema."""
    response = client.post(
        "/api/agent/understand",
        json={"message": "I want wireless headphones under 5000 rupees"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "intent" in data
    assert data["intent"]["intent"] == "product_search"


def test_product_search_intent_and_keywords(client):
    """Verify search query and intent extraction."""
    response = client.post(
        "/api/agent/understand",
        json={"message": "Show me mechanical keyboards"},
    )
    assert response.status_code == 200
    intent = response.json()["intent"]
    assert intent["intent"] == "product_search"
    assert "keyboard" in intent["search_query"].lower()
    assert intent["category"] == "Computer Accessories"


def test_price_extraction_under_bound(client):
    """Verify upper price bound extraction."""
    response = client.post(
        "/api/agent/understand",
        json={"message": "Find headphones under ₹4000"},
    )
    assert response.status_code == 200
    intent = response.json()["intent"]
    assert intent["max_price"] == "4000.0"
    assert intent["min_price"] is None


def test_price_extraction_range(client):
    """Verify range price extraction (between X and Y)."""
    response = client.post(
        "/api/agent/understand",
        json={"message": "Find computer accessories between ₹1000 and ₹5000"},
    )
    assert response.status_code == 200
    intent = response.json()["intent"]
    assert intent["min_price"] == "1000.0"
    assert intent["max_price"] == "5000.0"


def test_category_extraction(client):
    """Verify correct categorization across various product types."""
    categories_tests = [
        ("I need a rugged travel backpack", "Work & Travel"),
        ("Looking for 65W fast charger and cable", "Chargers & Cables"),
        ("Show me wireless earbuds", "Audio"),
        ("Titanium ergonomic laptop stand", "Computer Accessories"),
    ]
    for msg, expected_cat in categories_tests:
        resp = client.post("/api/agent/understand", json={"message": msg})
        assert resp.status_code == 200
        assert resp.json()["intent"]["category"] == expected_cat


def test_currency_defaults_to_inr(client):
    """Verify currency is INR by default."""
    response = client.post(
        "/api/agent/understand",
        json={"message": "USB-C charging cable under 600"},
    )
    assert response.status_code == 200
    assert response.json()["intent"]["currency"] == "INR"


def test_missing_information_remains_null(client):
    """Verify missing optional fields remain null rather than hallucinated."""
    response = client.post(
        "/api/agent/understand",
        json={"message": "Show me headphones"},
    )
    assert response.status_code == 200
    intent = response.json()["intent"]
    assert intent["min_price"] is None
    assert intent["max_price"] is None


def test_general_non_shopping_message(client):
    """Verify non-shopping general greetings return 'general' intent without product fabrication."""
    response = client.post(
        "/api/agent/understand",
        json={"message": "Hello, how are you today?"},
    )
    assert response.status_code == 200
    intent = response.json()["intent"]
    assert intent["intent"] == "general"
    assert intent["search_query"] is None
    assert intent["category"] is None
    assert intent["min_price"] is None
    assert intent["max_price"] is None


def test_empty_message_rejected(client):
    """Verify empty or whitespace-only messages are rejected with 422."""
    resp_empty = client.post("/api/agent/understand", json={"message": ""})
    assert resp_empty.status_code == 422

    resp_spaces = client.post("/api/agent/understand", json={"message": "   "})
    assert resp_spaces.status_code == 422


def test_schema_rejects_invalid_price_range():
    """Verify ShoppingIntent model validator rejects min_price > max_price."""
    with pytest.raises(ValidationError):
        ShoppingIntent(
            intent="product_search",
            min_price=Decimal("1000"),
            max_price=Decimal("500"),
        )


def test_ai_provider_configuration_failure():
    """Verify unconfigured or invalid AI provider raises controlled AIConfigurationError."""
    service = AIAgentService()
    service._provider = None

    class BrokenProvider(BaseAIProvider):
        async def extract_intent(self, message: str) -> AgentUnderstandResponse:
            raise AIConfigurationError(
                "AI service is not configured. Please set AI_API_KEY."
            )

    custom_service = AIAgentService(provider=BrokenProvider())
    with pytest.raises(AIConfigurationError):
        import asyncio
        asyncio.run(custom_service.understand_user_message("test"))


def test_ai_provider_error_handling(client, monkeypatch):
    """Verify provider runtime failure is converted to safe HTTP 502/503 without leaking stack traces."""
    class FailingProvider(BaseAIProvider):
        async def extract_intent(self, message: str) -> AgentUnderstandResponse:
            raise AIProviderError("External AI provider timeout")

    from app.services import ai_agent_service
    monkeypatch.setattr(ai_agent_service, "_provider", FailingProvider())

    response = client.post(
        "/api/agent/understand",
        json={"message": "I want headphones"},
    )
    assert response.status_code == 502
    assert "External AI provider timeout" in response.json()["detail"]


# === Agent Discovery Search Tests ===

def test_agent_search_normal(client):
    """Verify POST /api/agent/search finds specific product."""
    response = client.post(
        "/api/agent/search",
        json={"message": "I need wireless headphones"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"]["intent"] == "product_search"
    assert data["total"] >= 1
    assert any("Headphone" in item["name"] for item in data["items"])


def test_agent_search_category_filtering(client):
    """Verify category filtering via natural language query."""
    response = client.post(
        "/api/agent/search",
        json={"message": "I want something for travel"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"]["category"] == "Work & Travel"
    assert data["total"] == 3
    for item in data["items"]:
        assert item["category"] == "Work & Travel"


def test_agent_search_price_filtering(client):
    """Verify price bounded search via agent."""
    response = client.post(
        "/api/agent/search",
        json={"message": "Show me wireless earbuds under ₹5000"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert Decimal(item["price"]) <= Decimal("5000.00")
        assert "Earbuds" in item["name"] or "earbud" in item["description"].lower()


def test_agent_search_combined_filters(client):
    """Verify combined category, price range, and keyword query."""
    response = client.post(
        "/api/agent/search",
        json={"message": "Find computer accessories between ₹1000 and ₹5000"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    for item in data["items"]:
        assert item["category"] == "Computer Accessories"
        assert Decimal("1000.00") <= Decimal(item["price"]) <= Decimal("5000.00")


def test_agent_search_availability(client):
    """Verify agent search only returns in-stock active items."""
    response = client.post(
        "/api/agent/search",
        json={"message": "Show me products"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 14
    for item in data["items"]:
        assert item["is_active"] is True
        assert item["inventory"] > 0


def test_agent_search_non_product_intent(client):
    """Verify general greeting returns 200 with empty product list and conversational reply."""
    response = client.post(
        "/api/agent/search",
        json={"message": "Hello, how are you?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"]["intent"] == "general"
    assert data["total"] == 0
    assert data["items"] == []
    assert "AI Shopping Assistant" in data["message"]


def test_agent_search_no_matching_products(client):
    """Verify searching for out-of-budget or non-existent items returns total 0 cleanly."""
    response = client.post(
        "/api/agent/search",
        json={"message": "Find headphones under ₹500"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert "No products found" in data["message"]


def test_agent_search_invalid_request(client):
    """Verify empty message in search is rejected with HTTP 422."""
    response = client.post(
        "/api/agent/search",
        json={"message": ""},
    )
    assert response.status_code == 422
