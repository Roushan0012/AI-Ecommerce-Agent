from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.schemas.agent import (
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
    return TestClient(app)


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
