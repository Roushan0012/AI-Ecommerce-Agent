# AI Shopping Assistant and Intent Search

## 1. Overview

The AI Shopping Assistant enables conversational product discovery by transforming unstructured natural-language shopper queries into structured database queries. Shoppers are not constrained to strict categorical filters or keyword syntax; they can describe their requirements using conversational English, including price constraints, categories, and technical attributes.

The search architecture is implemented across `app/services/ai_agent.py`, `app/services/agent_guardrails.py`, and `app/api/agent.py`.

---

## 2. Intent Extraction Pipeline

The intent extraction pipeline operates in three consecutive stages:

```
[Shopper Input Query]
        |
        v
[1. Input Sanitization & Guardrails]
    - Strips leading/trailing whitespace
    - Checks length bounds (max 500 characters)
    - Removes dangerous control characters
        |
        v
[2. Intent Extraction Provider]
    +-------------------------------------------------------------+
    | Mode A: MockAIProvider (Default / Offline / Zero-Latency)  |
    | - Regex rule-based intent and parameter parsing             |
    | - Deterministic token normalization                         |
    | - Category keyword mapping                                  |
    | - Numerical price pattern matching                          |
    +-------------------------------------------------------------+
    | Mode B: OpenAICompatibleProvider (Configurable LLM)         |
    | - Communicates with OpenAI, Groq, or OpenRouter via HTTP    |
    | - Strict JSON-mode system prompt enforcement                |
    +-------------------------------------------------------------+
        |
        v
[3. ShoppingIntent Schema Validation]
    - Validates types and constraints via Pydantic
    - Reconciles min/max price bounds (min_price <= max_price)
    - Sets availability_required = True
        |
        v
[Structured ShoppingIntent Object]
```

---

## 3. Implementation Details: Deterministic Heuristics vs. External LLM

### 3.1 Provider Architecture
The platform abstracts AI provider operations behind the `BaseAIProvider` interface:
- `MockAIProvider`: A zero-dependency, deterministic heuristic parser that runs locally in-process without network overhead or API key requirements. This is the default provider used in testing, CI/CD, and offline demonstration.
- `OpenAICompatibleProvider`: An asynchronous HTTP client using `httpx` that posts prompts to an OpenAI-compatible `/chat/completions` endpoint with `response_format={"type": "json_object"}`. Supported backends include OpenAI (`gpt-4o-mini`), Groq (`openai/gpt-oss-120b`), and OpenRouter.

### 3.2 Provider Selection Logic
Provider selection is governed dynamically in `AIAgentService.get_provider()` based on environment settings:
- If `AI_PROVIDER == "mock"`: Instantiates `MockAIProvider()`.
- If `AI_PROVIDER` is `"openai"`, `"groq"`, `"openrouter"` or if `AI_API_KEY` is present: Instantiates `OpenAICompatibleProvider` with auto-detected base URLs and model defaults.
- If unconfigured in non-mock mode: Raises `AIConfigurationError`.

---

## 4. Extraction Mechanics in `MockAIProvider`

The deterministic parser executes specific regular expression extractors:

### 4.1 Conversational and Greeting Filtering
Queries matching greeting patterns (e.g., "hi", "hello", "hey", "who are you", "what can you do", "thanks") that do not contain product keywords return an immediate conversational response with `intent="general"` and bypass catalog database queries.

### 4.2 Category Detection
The parser maps common consumer terminology to catalog categories:
- `Audio`: Matched on "headphone", "earbud", "speaker", "audio", "sound", "earphones", "anc".
- `Computer Accessories`: Matched on "keyboard", "mouse", "desk mat", "laptop stand", "computer accessories", "laptop".
- `Chargers & Cables`: Matched on "charger", "cable", "gan", "dock", "hub", "usb-c", "power".
- `Work & Travel`: Matched on "backpack", "pouch", "flask", "travel", "organizer", "bottle".

### 4.3 Budget and Price Range Extraction
Price ceilings and floors are parsed using multi-pattern regex:
- Range syntax: Matches "between ₹X and ₹Y" or "X to Y", enforcing `min_price <= max_price`.
- Ceiling syntax: Matches "under ₹X", "below X", "less than X", "max X", "up to X", "within X".
- Floor syntax: Matches "above ₹X", "more than X", "over X", "min X", "starting from X".
- Abbreviation support: Parses "k" suffixes (e.g., "under 5k" is converted to `5000.00`).

### 4.4 Search Keyword Sanitization
- Removes filler phrases such as "i want", "i need", "looking for", "show me", "find me", "can you find".
- Strips trailing budget phrases (e.g., "under 5000 inr").
- Removes punctuation while preserving hyphens (e.g., "usb-c").
- Normalizes trailing plurals ("headphones" -> "headphone", "keyboards" -> "keyboard", "chargers" -> "charger") to maximize substring matches against product titles.
- Clears the search keyword if it merely duplicates the detected category name (e.g., query "accessories" with category "Computer Accessories" sets `search_query=None` so the broader category filter acts cleanly).

---

## 5. Catalog Search Execution

Once a structured `ShoppingIntent` is produced, the endpoint (`POST /api/agent/search`) delegates to `ProductService.list_products()`:

```python
products_res = product_service.list_products(
    db=db,
    search=intent.search_query,
    category=intent.category,
    min_price=intent.min_price,
    max_price=intent.max_price,
    available=intent.availability_required,
    page=request.page,
    page_size=request.page_size,
)
```

### Database Filter Construction
The service translates the intent into parameterized SQLAlchemy select statements:
- `search`: Applied as case-insensitive substring matching (`ILIKE`) against `Product.name` and `Product.description`.
- `category`: Matches `Product.category == category`.
- `min_price`: Adds `Product.price >= min_price`.
- `max_price`: Adds `Product.price <= max_price`.
- `available`: Adds `Product.inventory > 0` and `Product.is_active == True`.

---

## 6. Request and Response Contracts

### Request: `POST /api/agent/search`
```json
{
  "message": "Mechanical keyboard under 5000 with RGB",
  "page": 1,
  "page_size": 10
}
```

### Response: `200 OK`
```json
{
  "message": "Found 2 product(s) matching your request.",
  "intent": {
    "intent": "product_search",
    "search_query": "mechanical keyboard rgb",
    "category": "Computer Accessories",
    "min_price": null,
    "max_price": "5000.00",
    "currency": "INR",
    "availability_required": true
  },
  "items": [
    {
      "id": "c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
      "merchant_id": "m1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
      "name": "Keychron K2 Mechanical Keyboard",
      "description": "Compact 75% layout with RGB backlighting and hot-swappable switches.",
      "category": "Computer Accessories",
      "price": "4499.00",
      "currency": "INR",
      "inventory": 25,
      "sku": "ACC-KB-K2",
      "attributes": {
        "switch": "Gateron Brown",
        "layout": "75%",
        "backlight": "RGB"
      },
      "is_active": true,
      "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3",
      "created_at": "2026-09-01T00:00:00Z",
      "updated_at": "2026-09-01T00:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10
}
```

---

## 7. Audit Logging

Every execution of the agent search pipeline logs two distinct events in the `audit_logs` table:
1. `USER_REQUEST`: Captures the sanitized incoming prompt and requested pagination parameters.
2. `INTENT_DETECTED` or `TOOL_RESULT`: Captures the extracted `ShoppingIntent` and the total number of matched catalog items.
If an error occurs, an `ERROR` audit log entry is persisted containing the error message and execution status.
