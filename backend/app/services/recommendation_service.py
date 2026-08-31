import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.schemas.agent import RecommendedProductItem, ShoppingIntent
from app.schemas.product import ProductResponse
from app.services.product_service import product_service


def _json_attr_to_text(attributes: Optional[Dict[str, Any]]) -> str:
    """Flattens dictionary attributes into searchable text."""
    if not attributes or not isinstance(attributes, dict):
        return ""
    parts = []
    for k, v in attributes.items():
        if isinstance(v, (str, int, float, bool)):
            parts.append(f"{k} {v}")
        elif isinstance(v, list):
            parts.append(f"{k} {' '.join(str(i) for i in v)}")
    return " ".join(parts)


class RecommendationService:
    """
    Deterministic, explainable product recommendation and ranking engine.
    Scores candidates on:
    - Hard constraints adherence (active, in-stock, budget)
    - Category alignment (30%)
    - Text and attribute keyword relevance (35%)
    - Price proximity and budget value (20%)
    - Inventory health (15%)
    """

    STOP_WORDS = {
        "i", "me", "my", "we", "our", "you", "your", "he", "she", "it", "they",
        "want", "need", "looking", "for", "find", "show", "give", "get", "buy",
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "with",
        "under", "below", "above", "between", "less", "more", "than", "up",
        "rupees", "rs", "inr", "bucks", "price", "budget", "cost", "cheap",
        "something", "anything", "please", "can", "do", "have", "some", "good",
    }

    @classmethod
    def _extract_query_tokens(cls, text: str) -> List[str]:
        words = re.findall(r"\b[a-zA-Z0-9-]+\b", text.lower())
        return [w for w in words if w not in cls.STOP_WORDS and len(w) > 1]

    @classmethod
    def score_product(
        cls,
        product: ProductResponse,
        intent: ShoppingIntent,
        user_message: str,
    ) -> Tuple[float, str]:
        """
        Computes a deterministic score (0.0 to 1.0) and generates an explainable reason.
        Returns (0.0, reason) if hard constraints are violated.
        """
        # Hard Constraints Check
        if not product.is_active:
            return 0.0, "Product is inactive"

        if intent.availability_required and product.inventory <= 0:
            return 0.0, "Product is out of stock"

        if intent.max_price is not None and product.price > intent.max_price:
            return 0.0, f"Price (₹{product.price:,.0f}) exceeds max budget of ₹{intent.max_price:,.0f}"

        if intent.min_price is not None and product.price < intent.min_price:
            return 0.0, f"Price (₹{product.price:,.0f}) is below minimum threshold of ₹{intent.min_price:,.0f}"

        reasons_list = []

        # 1. Category Score (Weight: 0.30)
        if intent.category:
            if product.category and product.category.lower() == intent.category.lower():
                category_score = 0.30
                reasons_list.append(f"Matches category '{product.category}'")
            else:
                category_score = 0.05
        else:
            category_score = 0.20

        # 2. Text / Keyword Relevance (Weight: 0.35)
        text_tokens = cls._extract_query_tokens(f"{intent.search_query or ''} {user_message}")
        matched_tokens = set()

        title_lower = product.name.lower()
        desc_lower = (product.description or "").lower()
        attr_text = _json_attr_to_text(product.attributes).lower()

        title_matches = 0
        desc_matches = 0
        attr_matches = 0

        for token in text_tokens:
            stem = token[:-1] if token.endswith("s") and len(token) > 3 else token
            if token in title_lower or stem in title_lower:
                title_matches += 1
                matched_tokens.add(token)
            elif token in desc_lower or stem in desc_lower:
                desc_matches += 1
                matched_tokens.add(token)
            elif token in attr_text or stem in attr_text:
                attr_matches += 1
                matched_tokens.add(token)

        total_tokens = len(text_tokens) if text_tokens else 1
        title_contrib = min(0.20, (title_matches / total_tokens) * 0.25)
        desc_contrib = min(0.10, (desc_matches / total_tokens) * 0.15)
        attr_contrib = min(0.05, (attr_matches / total_tokens) * 0.10)
        keyword_score = title_contrib + desc_contrib + attr_contrib

        if matched_tokens:
            keywords_str = ", ".join(f"'{k}'" for k in list(matched_tokens)[:3])
            reasons_list.append(f"matched keywords {keywords_str}")

        # 3. Price Proximity / Budget Fitness (Weight: 0.20)
        price_score = 0.15
        if intent.max_price is not None:
            if intent.min_price is not None:
                price_score = 0.20
                reasons_list.append(f"within ₹{intent.min_price:,.0f}–₹{intent.max_price:,.0f} budget")
            else:
                price_ratio = float(product.price / intent.max_price)
                if 0.4 <= price_ratio <= 1.0:
                    price_score = 0.20
                else:
                    price_score = 0.15
                reasons_list.append(f"within budget (₹{product.price:,.0f} <= ₹{intent.max_price:,.0f})")
        elif intent.min_price is not None:
            price_score = 0.20
            reasons_list.append(f"above minimum ₹{intent.min_price:,.0f}")

        # 4. Inventory Health (Weight: 0.15)
        inv_score = 0.0
        if product.inventory >= 50:
            inv_score = 0.15
        elif product.inventory >= 10:
            inv_score = 0.10
        elif product.inventory > 0:
            inv_score = 0.05

        if product.inventory > 0:
            reasons_list.append(f"available in stock ({product.inventory} units)")

        total_score = round(min(1.0, category_score + keyword_score + price_score + inv_score), 2)
        reason = "; ".join(reasons_list) if reasons_list else "Recommended product from catalog"

        return total_score, reason

    @classmethod
    def recommend_products(
        cls,
        db: Session,
        intent: ShoppingIntent,
        user_message: str,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[RecommendedProductItem], int]:
        """
        Discovers product candidates, applies deterministic ranking, and returns paginated recommendations.
        """
        # Fetch candidate products adhering to intent constraints
        candidates_res = product_service.list_products(
            db=db,
            search=None,  # Broad candidate retrieval to rank via multi-factor scoring
            category=intent.category,
            min_price=intent.min_price,
            max_price=intent.max_price,
            available=intent.availability_required,
            page=1,
            page_size=100,
        )

        scored_items: List[RecommendedProductItem] = []
        for prod in candidates_res.items:
            score, reason = cls.score_product(prod, intent, user_message)
            if score > 0.0:
                scored_items.append(
                    RecommendedProductItem(
                        product=prod,
                        score=score,
                        reason=reason,
                    )
                )

        # If strict category filtering yielded no results, explore across all categories
        if not scored_items and intent.category:
            fallback_candidates = product_service.list_products(
                db=db,
                search=None,
                category=None,
                min_price=intent.min_price,
                max_price=intent.max_price,
                available=intent.availability_required,
                page=1,
                page_size=100,
            )
            for prod in fallback_candidates.items:
                score, reason = cls.score_product(prod, intent, user_message)
                if score > 0.0:
                    scored_items.append(
                        RecommendedProductItem(
                            product=prod,
                            score=score,
                            reason=reason,
                        )
                    )

        # Deterministic Ranking: score descending, price ascending, product ID ascending
        scored_items.sort(
            key=lambda x: (
                -x.score,
                x.product.price,
                str(x.product.id),
            )
        )

        total = len(scored_items)
        offset = (page - 1) * page_size
        paginated_items = scored_items[offset : offset + page_size]

        return paginated_items, total


recommendation_service = RecommendationService()
