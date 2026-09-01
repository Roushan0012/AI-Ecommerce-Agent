import pytest
from app.services.ai_agent import ai_agent_service, MockAIProvider


@pytest.fixture(autouse=True)
def set_mock_ai_provider_for_tests():
    """Ensure all automated tests use deterministic MockAIProvider."""
    prev_provider = ai_agent_service._provider
    ai_agent_service._provider = MockAIProvider()
    yield
    ai_agent_service._provider = prev_provider
