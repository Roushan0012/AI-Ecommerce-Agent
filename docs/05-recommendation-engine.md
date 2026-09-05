# AI Recommendation Engine

## 1. Overview

The AI Recommendation Engine (`POST /api/agent/recommend`) generates ranked product recommendations with transparent, human-readable explainability rationale strings. Unlike standard relational sorting (which orders solely by price or date), the recommendation service scores candidate products using a deterministic multi-factor algorithm balancing category match, text and attribute relevance, price proximity, and stock health.

The service implementation resides in `backend/app/services/recommendation_service.py` and is exposed via `backend/app/api/agent.py`.

---

## 2. Recommendation Pipeline

```
[User Natural-Language Request]
               |
               v
[Intent Extraction & Sanitization] -> Produces ShoppingIntent
               |
               v
[Broad Candidate Retrieval] --------> Queries DB with category & budget bounds (limit 100)
               |
               v
[Hard Constraints Filter] ----------> Prunes inactive, out-of-stock, or out-of-budget products
               |
               v
[Multi-Factor Scoring Engine] ------> Category (0.30) + Keywords (0.35) + Budget (0.20) + Inventory (0.15)
               |
               v
[Fallback Broadening] --------------> If strict category yields 0 matches, broaden across all categories
               |
               v
[Deterministic Ranking] ------------> Sort by: Score (desc) -> Price (asc) -> Product ID (asc)
               |
               v
[Pagination & Response] ------------> Returns RecommendedProductItem list with scores & rationales
```

---

## 3. Candidate Selection Strategy

To score products holistically rather than relying on strict SQL text filtering, candidate products are retrieved broadly via `ProductService.list_products()`:
- `category`: Matches `intent.category` if detected.
- `min_price` / `max_price`: Passes budget bounds.
- `available`: Restricts to active products with `inventory > 0`.
- `page_size`: Fetches up to 100 candidate items for in-memory scoring.

### Fallback Broadening Mechanism
If the shopper requested a category that yields zero matching products, the recommendation engine automatically broadens the search scope across all catalog categories. Candidates are re-evaluated against the shopper's query and budget, ensuring the shopper receives viable alternatives rather than an empty response.

---

## 4. Authoritative Scoring Function

Every candidate product is evaluated by `RecommendationService.score_product()`.

### 4.1 Hard Constraint Checks
Before weighted scoring begins, hard business constraints are verified. If any check fails, the product is assigned a score of `0.0` and excluded:
1. Product Active Check: If `not product.is_active`, returns `(0.0, "Product is inactive")`.
2. Availability Check: If `intent.availability_required and product.inventory <= 0`, returns `(0.0, "Product is out of stock")`.
3. Budget Ceiling Check: If `intent.max_price is not None and product.price > intent.max_price`, returns `(0.0, "Price exceeds max budget")`.
4. Budget Floor Check: If `intent.min_price is not None and product.price < intent.min_price`, returns `(0.0, "Price is below minimum threshold")`.

### 4.2 Weighted Scoring Dimensions

When hard constraints pass, the composite score is calculated:

```
Final Score = min(1.0, CategoryScore + KeywordScore + PriceScore + InventoryScore)
```

The composite score is rounded to two decimal places (`0.00` to `1.00`).

#### Factor 1: Category Score (Maximum Contribution: 0.30)
- Intent specifies a category:
  - If `product.category.lower() == intent.category.lower()`: Contributes `0.30` and appends `"Matches category '{product.category}'"` to the rationale.
  - If categories mismatch: Contributes `0.05`.
- Intent does not specify a category: Contributes a neutral baseline of `0.20`.

#### Factor 2: Text and Attribute Keyword Relevance (Maximum Contribution: 0.35)
Extracts query tokens from the user's message and search intent, filtering out common stop words ("want", "need", "looking", "buy", "under", "price", "rupees", etc.). Compares stemmed tokens against three product text fields:
1. Product Title (`product.name`): Contributes up to `0.20` (`min(0.20, (title_matches / total_tokens) * 0.25)`).
2. Product Description (`product.description`): Contributes up to `0.10` (`min(0.10, (desc_matches / total_tokens) * 0.15)`).
3. Product Technical Attributes (`product.attributes` JSONB): Flattens attribute keys and values into searchable text, contributing up to `0.05` (`min(0.05, (attr_matches / total_tokens) * 0.10)`).
When matches are found, the top matched keywords are appended to the rationale (e.g., `"matched keywords 'mechanical', 'rgb'"`).

#### Factor 3: Price Proximity and Budget Fitness (Maximum Contribution: 0.20)
- Bounded Range (`min_price` and `max_price` both provided): Contributes `0.20` and appends `"within ₹X–₹Y budget"`.
- Price Ceiling Only (`max_price` provided):
  - If `0.4 <= (price / max_price) <= 1.0`: Contributes `0.20` (optimal price bracket).
  - If `(price / max_price) < 0.4`: Contributes `0.15` (acceptable, but significantly cheaper).
  - Appends `"within budget (₹X <= ₹Y)"`.
- Price Floor Only (`min_price` provided): Contributes `0.20` and appends `"above minimum ₹X"`.
- No budget specified: Default baseline contribution of `0.15`.

#### Factor 4: Inventory Health (Maximum Contribution: 0.15)
Reflects physical inventory depth to reward reliably stocked items:
- Deep stock (`inventory >= 50`): Contributes `0.15`.
- Adequate stock (`10 <= inventory < 50`): Contributes `0.10`.
- Low stock (`0 < inventory < 10`): Contributes `0.05`.
- Zero stock (`inventory <= 0`): Contributes `0.00`.
Appends `"available in stock (N units)"` to the rationale string.

---

## 5. Deterministic Ranking Strategy

To eliminate non-deterministic ordering and ensure reproducible test outcomes, scored candidate products are sorted using a multi-attribute tuple:
1. Score Descending (`-x.score`): Highest composite score appears first.
2. Price Ascending (`x.product.price`): Lower price breaks ties among identical scores.
3. Product ID Ascending (`str(x.product.id)`): Ensures stable ordering for identical prices.

---

## 6. Request and Response Contracts

### Request: `POST /api/agent/recommend`
```json
{
  "message": "Ergonomic wireless mouse for office work under 3000",
  "page": 1,
  "page_size": 5
}
```

### Response: `200 OK`
```json
{
  "message": "Found 2 top recommendation(s) for your request.",
  "intent": {
    "intent": "product_search",
    "search_query": "ergonomic wireless mouse office work",
    "category": "Computer Accessories",
    "min_price": null,
    "max_price": "3000.00",
    "currency": "INR",
    "availability_required": true
  },
  "items": [
    {
      "product": {
        "id": "e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b",
        "merchant_id": "m1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
        "name": "Logitech Lift Vertical Ergonomic Mouse",
        "description": "Wireless vertical mouse designed for small to medium hands with silent clicks.",
        "category": "Computer Accessories",
        "price": "2799.00",
        "currency": "INR",
        "inventory": 45,
        "sku": "ACC-PG-LIFT",
        "attributes": {
          "connectivity": "Bluetooth & Logi Bolt",
          "sensor": "Optical",
          "dpi": "4000"
        },
        "is_active": true,
        "image_url": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7",
        "created_at": "2026-09-01T00:00:00Z",
        "updated_at": "2026-09-01T00:00:00Z"
      },
      "score": 0.88,
      "reason": "Matches category 'Computer Accessories'; matched keywords 'ergonomic', 'wireless', 'mouse'; within budget (₹2,799 <= ₹3,000); available in stock (45 units)"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 5
}
```

---

## 7. Frontend Integration

In the Next.js storefront (`frontend/src/app/page.tsx`):
- Mode Toggle: Shoppers activate "Top AI Picks" by clicking the dedicated mode button (`ai-mode-recommend-btn`).
- Recommendation Card: Displays the product image, title, price, category tag, and stock status.
- Match Badge: Converts `score` into a visual match percentage (`Math.round(item.score * 100)% Match`).
- Explainability Badge: Renders the backend `reason` string directly beneath the product title, explaining why the system selected it.
- Direct Add to Cart: Reuses the authenticated cart synchronization pipeline, immediately adding the recommended product to the user's persistent cart drawer.
