# AI Growth Engine (Upsell and Cross-Sell)

## 1. Overview

The AI Growth Engine (`POST /api/agent/growth`) drives merchant Average Order Value (AOV) and customer purchasing utility by automatically generating contextual upsell and cross-sell opportunities. The service analyzes products the shopper is considering and calculates:
1. Upsells: Higher-specification, premium alternatives within the same product category that fit within the shopper's budget.
2. Cross-Sells: Compatible companion accessories across complementary functional categories.

The growth engine is implemented in `backend/app/services/growth_service.py` and exposed via `backend/app/api/agent.py`.

---

## 2. Core Differences: Upsell vs. Cross-Sell

| Attribute | Upsell | Cross-Sell |
|---|---|---|
| Objective | Encourage shopper to choose a higher-tier model with superior specifications | Encourage shopper to add companion products that complement the primary purchase |
| Target Category | Identical to primary product category | Complementary accessory categories based on functional affinity rules |
| Price Relationship | Higher than primary product (`candidate.price > primary.price`), bounded by 4.5x or budget | Typically lower than or proportionate to primary product price |
| Value Proposition | "Better performance, more features, higher durability for an incremental price step" | "Essential companion, protective case, cables, or workflow enhancer" |
| Scoring Mechanism | Base 0.70 + specification improvements (up to 0.20) + inventory health (up to 0.10) | Rule-based affinity score (0.68 to 0.94) derived from verified pairing rules |

---

## 3. Upsell Engine Implementation

### 3.1 Candidate Selection Rules
To qualify as an upsell recommendation for a primary product, a candidate product must satisfy all of the following conditions:
1. Hard Constraints:
   - `candidate.is_active == True`
   - `candidate.inventory > 0`
   - Must not be already in the excluded items set (prevents duplicate recommendations).
   - If user specified `max_price`, `candidate.price <= max_price`.
2. Category Match:
   - `(candidate.category or "").lower() == (primary_product.category or "").lower()`
3. True Price Step:
   - `candidate.price > primary_product.price` (strictly more expensive).
4. Price Jump Ceiling:
   - `(candidate.price / primary_product.price) <= 4.5` (if no explicit user budget ceiling is specified).

### 3.2 Specification Comparison Logic
The upsell engine inspects the JSONB `attributes` dictionaries of both the primary product and candidate product using `_explain_upsell_improvement()`:
- Power Output (e.g., Chargers): Compares `total_output` (e.g., 100W vs 65W) or port counts. Adds up to `+0.08` to score.
- Audio Capabilities (e.g., Headphones): Detects `noise_cancellation` (hybrid active noise cancellation vs passive), driver sizes (`50mm` vs `40mm`), or extended battery life (`40h` vs `25h`). Adds up to `+0.09` to score.
- Workstation Accessories: Compares switch types (hot-swappable mechanical vs membrane), wireless protocols (Bluetooth 5.3 + 2.4GHz vs wired), or sensor resolution (4000 DPI vs 1600 DPI).
- Storage / Capacity: Compares capacity attributes (e.g., 30L vs 20L backpack).

### 3.3 Upsell Scoring Formula
```
Total Upsell Score = min(1.0, 0.70 + SpecificationScore + InventoryContribution)
```
- Base Score: `0.70`
- Specification Improvement: `0.10` to `0.20` based on attribute evaluation.
- Inventory Health: `0.10` if `inventory >= 40`; otherwise `0.05`.

---

## 4. Cross-Sell Engine Implementation

### 4.1 Explicit Category Affinity Rules (`CROSS_SELL_RULES`)
Cross-sell pairings are governed by deterministic rule sets defined in `GrowthRecommendationService.CROSS_SELL_RULES`:

```python
CROSS_SELL_RULES = [
    # 1. Audio Products -> Travel Organizer, 100W Braided Cable, GaN Fast Charger, Travel Flask
    {
        "match_category": "Audio",
        "match_keywords": ["headphone", "earbud", "speaker", "audio", "sound"],
        "complement_rules": [
            {"target_sku_prefix": "TRV-OP", "target_keywords": ["organizer", "pouch"], "score": 0.88},
            {"target_sku_prefix": "CHG-PA", "target_keywords": ["cable", "braided"], "score": 0.84},
            {"target_sku_prefix": "CHG-VF", "target_keywords": ["charger", "gan"], "score": 0.78},
            {"target_sku_prefix": "TRV-HS", "target_keywords": ["flask", "bottle"], "score": 0.68},
        ],
    },
    # 2. Keyboards -> Ergonomic Mouse, Felt Desk Mat, USB-C Dock/Hub
    {
        "match_category": "Computer Accessories",
        "match_keywords": ["keyboard"],
        "complement_rules": [
            {"target_sku_prefix": "ACC-PG", "target_keywords": ["mouse", "ergonomic"], "score": 0.92},
            {"target_sku_prefix": "ACC-UG", "target_keywords": ["desk mat", "felt", "pad"], "score": 0.88},
            {"target_sku_prefix": "CHG-OL", "target_keywords": ["hub", "dock"], "score": 0.80},
        ],
    },
    # 3. Mouse -> Felt Desk Mat, Mechanical Keyboard, Aluminum Laptop Stand
    {
        "match_category": "Computer Accessories",
        "match_keywords": ["mouse"],
        "complement_rules": [
            {"target_sku_prefix": "ACC-UG", "target_keywords": ["desk mat", "felt", "pad"], "score": 0.92},
            {"target_sku_prefix": "ACC-EP", "target_keywords": ["keyboard", "mechanical"], "score": 0.86},
            {"target_sku_prefix": "ACC-TF", "target_keywords": ["laptop stand", "stand"], "score": 0.82},
        ],
    },
    # 4. Chargers -> Braided 100W Cable, Travel Organizer Pouch
    {
        "match_category": "Chargers & Cables",
        "match_keywords": ["charger", "gan", "power", "adapter"],
        "complement_rules": [
            {"target_sku_prefix": "CHG-PA", "target_keywords": ["cable", "braided"], "score": 0.94},
            {"target_sku_prefix": "TRV-OP", "target_keywords": ["organizer", "pouch"], "score": 0.86},
        ],
    },
    # 5. Work & Travel Backpacks -> Tech Organizer Pouch, Insulated Travel Flask, GaN Charger
    {
        "match_category": "Work & Travel",
        "match_keywords": ["backpack", "bag"],
        "complement_rules": [
            {"target_sku_prefix": "TRV-OP", "target_keywords": ["organizer", "pouch"], "score": 0.92},
            {"target_sku_prefix": "TRV-HS", "target_keywords": ["flask", "bottle"], "score": 0.88},
            {"target_sku_prefix": "CHG-VF", "target_keywords": ["charger", "gan"], "score": 0.80},
        ],
    },
]
```

### 4.2 Candidate Matching Process
1. Category and Keyword Trigger: Checks if the primary product matches `match_category` and contains any `match_keywords` in its title or description.
2. Companion Evaluation: Evaluates catalog candidates against each `complement_rules` entry.
3. Candidate Verification: Matches `target_sku_prefix` (e.g., `ACC-PG` for mice) or target keywords in candidate title/description.
4. Active Inventory Enforcement: Candidates with `inventory <= 0` are excluded.
5. Contextual Rationale Generation: Fills the rule's `reason_template` with the primary product's name (e.g., *"An extended felt desk mat provides a soft, protective surface and sound dampening for your Keychron K2 Mechanical Keyboard."*).

---

## 5. Request and Response Contracts

### Request: `POST /api/agent/growth`
```json
{
  "message": "Keychron mechanical keyboard",
  "page": 1,
  "page_size": 10
}
```

### Response: `200 OK`
```json
{
  "message": "I found suitable products and 3 useful upgrade and accessory options.",
  "intent": {
    "intent": "product_search",
    "search_query": "keychron mechanical keyboard",
    "category": "Computer Accessories",
    "min_price": null,
    "max_price": null,
    "currency": "INR",
    "availability_required": true
  },
  "primary_products": [
    {
      "id": "c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
      "name": "Keychron K2 Mechanical Keyboard",
      "category": "Computer Accessories",
      "price": "4499.00",
      "inventory": 25,
      "sku": "ACC-KB-K2"
    }
  ],
  "upsell": [
    {
      "type": "upsell",
      "product": {
        "id": "u1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
        "name": "Keychron Q1 Pro Custom Mechanical Keyboard",
        "category": "Computer Accessories",
        "price": "8999.00",
        "inventory": 18,
        "sku": "ACC-KB-Q1PRO"
      },
      "primary_product_id": "c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
      "primary_product_name": "Keychron K2 Mechanical Keyboard",
      "score": 0.88,
      "reason": "Premium upgrade: full CNC aluminum body with double-gasket acoustic mounting and hot-swappable switches for ₹4,500 additional."
    }
  ],
  "cross_sell": [
    {
      "type": "cross_sell",
      "product": {
        "id": "e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b",
        "name": "Logitech Lift Vertical Ergonomic Mouse",
        "category": "Computer Accessories",
        "price": "2799.00",
        "inventory": 45,
        "sku": "ACC-PG-LIFT"
      },
      "primary_product_id": "c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
      "primary_product_name": "Keychron K2 Mechanical Keyboard",
      "score": 0.92,
      "reason": "An ergonomic wireless mouse is the ideal productivity companion to pair with your Keychron K2 Mechanical Keyboard."
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 10
}
```

---

## 6. Frontend Integration

In the Next.js storefront (`frontend/src/app/page.tsx`):
- Mode Toggle: Activated via the "Upgrades & Accessories" button (`data-testid="ai-mode-growth-btn"`).
- Section Organization:
  - Reference Product: Highlights the primary product the shopper is evaluating.
  - Upgrade Options (Upsell Section): Renders upsell cards styled with upgrade badges, showing the price difference, specification improvements, and direct Add-to-Cart buttons.
  - Accessory Companions (Cross-Sell Section): Renders companion accessory cards with category affinity scores, pairing rationales, and Add-to-Cart buttons.
- Cart Synchronization: Adding an upsell or cross-sell item calls the authenticated cart API (`POST /api/cart/items`), instantly updating the persistent cart drawer without page refreshes.
