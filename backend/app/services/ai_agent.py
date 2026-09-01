import json
import re
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, Optional
import httpx
from app.core.config import settings
from app.core.prompts import SHOPPING_INTENT_SYSTEM_PROMPT
from app.schemas.agent import AgentUnderstandResponse, ShoppingIntent


class AIProviderError(Exception):
    """Raised when an external AI provider fails or returns malformed data."""
    pass


class AIConfigurationError(Exception):
    """Raised when the AI provider is misconfigured or missing credentials."""
    pass


class BaseAIProvider(ABC):
    """Abstract interface for AI intent extraction providers."""

    @abstractmethod
    async def extract_intent(self, message: str) -> AgentUnderstandResponse:
        """Extract structured shopping intent from a customer message."""
        pass


class MockAIProvider(BaseAIProvider):
    """
    Deterministic rule-based intent extraction provider.
    Used for unit testing, offline development, and zero-dependency verification.
    """

    async def extract_intent(self, message: str) -> AgentUnderstandResponse:
        cleaned_msg = message.strip()
        lower_msg = cleaned_msg.lower()

        # Check for general conversational / non-shopping queries
        general_patterns = [
            r"^(hi|hello|hey|greetings|good\s+(morning|afternoon|evening))\b",
            r"^how are you",
            r"^who are you",
            r"^what can you do",
            r"^(thanks|thank you)",
        ]
        if any(re.search(p, lower_msg) for p in general_patterns) and not any(
            w in lower_msg
            for w in [
                "buy", "need", "want", "find", "show", "search", "headphone",
                "earbud", "speaker", "keyboard", "mouse", "charger", "cable",
                "stand", "backpack", "flask", "pouch", "accessories", "price",
            ]
        ):
            return AgentUnderstandResponse(
                message="Hello! I am your AI Shopping Assistant. How can I help you find products today?",
                intent=ShoppingIntent(
                    intent="general",
                    search_query=None,
                    category=None,
                    min_price=None,
                    max_price=None,
                    currency="INR",
                    availability_required=True,
                ),
            )

        # Detect Category
        category = None
        if any(w in lower_msg for w in ["headphone", "earbud", "speaker", "audio", "sound", "earphones", "anc"]):
            category = "Audio"
        elif any(w in lower_msg for w in ["keyboard", "mouse", "desk mat", "laptop stand", "computer accessories", "laptop"]):
            category = "Computer Accessories"
        elif any(w in lower_msg for w in ["charger", "cable", "gan", "dock", "hub", "usb-c", "power"]):
            category = "Chargers & Cables"
        elif any(w in lower_msg for w in ["backpack", "pouch", "flask", "travel", "organizer", "bottle"]):
            category = "Work & Travel"

        # Detect Price Bounds
        min_price = None
        max_price = None

        # Pattern: between X and Y
        range_match = re.search(
            r"between\s*(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)?)\s*(?:and|to|-)\s*(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)?)",
            lower_msg,
        )
        if range_match:
            min_val = float(range_match.group(1).replace(",", ""))
            max_val = float(range_match.group(2).replace(",", ""))
            if min_val <= max_val:
                min_price = Decimal(str(min_val))
                max_price = Decimal(str(max_val))

        # Pattern: under / below / max / less than X
        if max_price is None:
            max_match = re.search(
                r"(?:under|below|less than|max|up to|within)\s*(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)?)\s*(?:rupees|rs|k)?",
                lower_msg,
            )
            if max_match:
                val_str = max_match.group(1).replace(",", "")
                val = float(val_str)
                # Handle 'k' notation if present e.g. 5k
                if "k" in max_match.group(0) and val < 1000:
                    val *= 1000
                max_price = Decimal(str(val))

        # Pattern: above / more than / min X
        if min_price is None:
            min_match = re.search(
                r"(?:above|more than|over|min|starting from|greater than)\s*(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)?)\s*(?:rupees|rs|k)?",
                lower_msg,
            )
            if min_match:
                val_str = min_match.group(1).replace(",", "")
                val = float(val_str)
                if "k" in min_match.group(0) and val < 1000:
                    val *= 1000
                min_price = Decimal(str(val))

        # Extract search query
        # Remove common filler phrases
        search_query = lower_msg
        clean_prefixes = [
            r"^(i want|i need|looking for|show me|find me|do you have|search for|can you find|give me|find)\s*",
            r"\b(under|below|between|above|more than|less than|within)\s*(?:₹|rs\.?|inr)?\s*\d+.*$",
            r"\b(in\s+inr|in\s+rupees|rupees|rs\.?|inr)\b",
        ]
        for cp in clean_prefixes:
            search_query = re.sub(cp, "", search_query, flags=re.IGNORECASE).strip()

        # Clean trailing/leading punctuation
        search_query = re.sub(r"[^\w\s-]", "", search_query).strip()

        # If search query is generic or merely restates the category name, clear it so category filter acts cleanly
        if category and (
            search_query in [category.lower(), "accessories", "products", "items", "something", "gear", "device", "devices"]
            or search_query == "something for travel"
        ):
            search_query = None
        elif search_query in ["something", "anything", "products", "items"]:
            search_query = None

        if search_query:
            # Normalize trailing plurals for robust catalog substring matching
            if search_query.endswith("chargers"):
                search_query = search_query[:-1]
            elif search_query.endswith("headphones"):
                search_query = search_query[:-1]
            elif search_query.endswith("earbuds"):
                search_query = search_query[:-1]
            elif search_query.endswith("speakers"):
                search_query = search_query[:-1]
            elif search_query.endswith("keyboards"):
                search_query = search_query[:-1]
            elif search_query.endswith("stands"):
                search_query = search_query[:-1]
            elif search_query.endswith("cables"):
                search_query = search_query[:-1]
            elif search_query.endswith("backpacks"):
                search_query = search_query[:-1]
            elif search_query.endswith("pouches"):
                search_query = search_query[:-2]
            elif search_query.endswith("flasks"):
                search_query = search_query[:-1]

        # Build assistant summary message
        price_summary = ""
        if min_price and max_price:
            price_summary = f" priced between ₹{min_price:,.0f} and ₹{max_price:,.0f}"
        elif max_price:
            price_summary = f" under ₹{max_price:,.0f}"
        elif min_price:
            price_summary = f" above ₹{min_price:,.0f}"

        cat_summary = f" in {category}" if category else ""
        query_summary = f"matching '{search_query}'" if search_query else "in catalog"
        assistant_msg = f"I found options {query_summary}{cat_summary}{price_summary}."

        intent_obj = ShoppingIntent(
            intent="product_search",
            search_query=search_query if search_query else None,
            category=category,
            min_price=min_price,
            max_price=max_price,
            currency="INR",
            availability_required=True,
        )

        return AgentUnderstandResponse(
            message=assistant_msg,
            intent=intent_obj,
        )


class OpenAICompatibleProvider(BaseAIProvider):
    """
    LLM provider using OpenAI-compatible REST API (OpenAI, Groq, OpenRouter, Ollama, etc.)
    Uses standard async HTTP client without heavy external SDK dependencies.
    """

    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        if not api_key:
            raise AIConfigurationError(
                "AI service is not configured. Please set AI_API_KEY in your backend/.env file."
            )
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    async def extract_intent(self, message: str) -> AgentUnderstandResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SHOPPING_INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
        except httpx.RequestError as e:
            raise AIProviderError(f"Failed to communicate with AI provider: {str(e)}")

        if response.status_code != 200:
            raise AIProviderError(
                f"AI provider returned error {response.status_code}: {response.text}"
            )

        try:
            res_json = response.json()
            raw_content = res_json["choices"][0]["message"]["content"]
            parsed_data = json.loads(raw_content)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise AIProviderError(f"AI provider returned malformed JSON response: {str(e)}")

        # Validate structured intent against Pydantic schema
        try:
            intent_data = parsed_data.get("intent", parsed_data)
            intent_obj = ShoppingIntent(**intent_data)
            summary_msg = parsed_data.get(
                "message",
                parsed_data.get(
                    "summary",
                    f"Understood request for {intent_obj.search_query or 'products'}",
                ),
            )
            return AgentUnderstandResponse(
                message=summary_msg,
                intent=intent_obj,
            )
        except Exception as e:
            raise AIProviderError(f"Structured output failed schema validation: {str(e)}")


class AIAgentService:
    """Service facade coordinating provider selection and intent understanding."""

    def __init__(self, provider: Optional[BaseAIProvider] = None):
        self._provider = provider

    def get_provider(self) -> BaseAIProvider:
        if self._provider is not None:
            return self._provider

        provider_name = settings.AI_PROVIDER
        if provider_name == "mock":
            return MockAIProvider()

        if provider_name in ["openai", "groq", "openrouter"] or settings.AI_API_KEY:
            api_key = settings.AI_API_KEY
            base_url = settings.AI_BASE_URL
            model = settings.AI_MODEL

            # Auto-detect Groq keys or Groq models
            if provider_name == "groq" or api_key.startswith("gsk_"):
                base_url = "https://api.groq.com/openai/v1"
                if not model or model == "gpt-4o-mini":
                    model = "openai/gpt-oss-120b"
            elif provider_name == "openrouter" or api_key.startswith("sk-or-"):
                base_url = "https://openrouter.ai/api/v1"
            elif api_key.startswith("sk-proj-") or (api_key.startswith("sk-") and not api_key.startswith("sk-or-")):
                # OpenAI key detected
                base_url = "https://api.openai.com/v1"
                if "llama" in model.lower() or not model:
                    model = "gpt-4o-mini"
            elif base_url and "openai.com" in base_url and "llama" in model.lower():
                # OpenAI base_url cannot run llama models; default to gpt-4o-mini
                model = "gpt-4o-mini"
            elif not base_url and "llama" in model.lower():
                base_url = "https://api.groq.com/openai/v1"

            return OpenAICompatibleProvider(
                api_key=api_key,
                model=model,
                base_url=base_url,
            )

        # Default fallback to mock with warning or provider error
        raise AIConfigurationError(
            f"Unsupported or unconfigured AI_PROVIDER: '{provider_name}'. Supported: mock, openai, groq, openrouter."
        )

    async def understand_user_message(self, message: str) -> AgentUnderstandResponse:
        """Processes customer message and returns validated structured intent."""
        provider = self.get_provider()
        return await provider.extract_intent(message)


ai_agent_service = AIAgentService()
