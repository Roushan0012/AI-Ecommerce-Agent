from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from app.schemas.agent import ShoppingIntent
from app.schemas.growth import GrowthRecommendationItem
from app.schemas.product import ProductResponse
from app.services.product_service import product_service
from app.services.recommendation_service import recommendation_service


class GrowthRecommendationService:
    """
    Deterministic, explainable Upsell and Cross-sell engine.
    - Upsell: Identifies higher-value, specification-improved alternatives in the same or closely related tier
      within explicit budget constraints.
    - Cross-sell: Identifies complementary companion products and accessories across functional roles.
    """

    # Complementary cross-sell pairings based on product category, keywords, and functional accessories
    CROSS_SELL_RULES = [
        # 1. Audio Products -> Travel Pouches, Braided Cables, GaN Chargers, Travel Flasks
        {
            "match_category": "Audio",
            "match_keywords": ["headphone", "earbud", "speaker", "audio", "sound"],
            "complement_rules": [
                {
                    "target_sku_prefix": "TRV-OP",
                    "target_keywords": ["organizer", "pouch"],
                    "score": 0.88,
                    "reason_template": "A protective tech organizer pouch keeps your {primary_name} and charging cables safe during commute and travel.",
                },
                {
                    "target_sku_prefix": "CHG-PA",
                    "target_keywords": ["cable", "braided"],
                    "score": 0.84,
                    "reason_template": "A durable 100W braided USB-C cable ensures fast, reliable recharging for your {primary_name}.",
                },
                {
                    "target_sku_prefix": "CHG-VF",
                    "target_keywords": ["charger", "gan"],
                    "score": 0.78,
                    "reason_template": "An ultra-compact GaN fast charger provides quick multi-device charging for your {primary_name}.",
                },
                {
                    "target_sku_prefix": "TRV-HS",
                    "target_keywords": ["flask", "bottle"],
                    "score": 0.68,
                    "reason_template": "An insulated stainless travel flask is a great companion for outdoor listening sessions.",
                },
            ],
        },
        # 2. Keyboards -> Mouse, Desk Mat, USB-C Hub
        {
            "match_category": "Computer Accessories",
            "match_keywords": ["keyboard"],
            "complement_rules": [
                {
                    "target_sku_prefix": "ACC-PG",
                    "target_keywords": ["mouse", "ergonomic"],
                    "score": 0.92,
                    "reason_template": "An ergonomic wireless mouse is the ideal productivity companion to pair with your {primary_name}.",
                },
                {
                    "target_sku_prefix": "ACC-UG",
                    "target_keywords": ["desk mat", "felt", "pad"],
                    "score": 0.88,
                    "reason_template": "An extended felt desk mat provides a soft, protective surface and sound dampening for your {primary_name}.",
                },
                {
                    "target_sku_prefix": "CHG-OL",
                    "target_keywords": ["hub", "dock"],
                    "score": 0.80,
                    "reason_template": "An 8-in-1 USB-C hub allows you to connect your keyboard and multi-display workstation seamlessly.",
                },
            ],
        },
        # 3. Mouse -> Desk Mat, Keyboard, Laptop Stand
        {
            "match_category": "Computer Accessories",
            "match_keywords": ["mouse"],
            "complement_rules": [
                {
                    "target_sku_prefix": "ACC-UG",
                    "target_keywords": ["desk mat", "felt", "pad"],
                    "score": 0.92,
                    "reason_template": "An extended wool felt desk mat ensures smooth optical tracking and wrist comfort for your {primary_name}.",
                },
                {
                    "target_sku_prefix": "ACC-EP",
                    "target_keywords": ["keyboard", "mechanical"],
                    "score": 0.86,
                    "reason_template": "Pairs with your ergonomic mouse to build a complete high-performance workstation.",
                },
                {
                    "target_sku_prefix": "ACC-TF",
                    "target_keywords": ["laptop stand", "stand"],
                    "score": 0.82,
                    "reason_template": "Elevates your screen to eye level while using your external {primary_name}.",
                },
            ],
        },
        # 4. Laptop Stand or Laptop context -> Mouse, Keyboard, USB-C Hub, Backpack
        {
            "match_category": "Computer Accessories",
            "match_keywords": ["laptop stand", "stand", "riser", "laptop"],
            "complement_rules": [
                {
                    "target_sku_prefix": "ACC-PG",
                    "target_keywords": ["mouse", "ergonomic"],
                    "score": 0.90,
                    "reason_template": "A precision wireless mouse enables comfortable posture while your laptop is elevated on the {primary_name}.",
                },
                {
                    "target_sku_prefix": "ACC-EP",
                    "target_keywords": ["keyboard", "mechanical"],
                    "score": 0.88,
                    "reason_template": "An external keyboard is essential for ergonomic typing when your laptop is mounted on the stand.",
                },
                {
                    "target_sku_prefix": "CHG-OL",
                    "target_keywords": ["hub", "dock"],
                    "score": 0.84,
                    "reason_template": "An 8-in-1 multi-port hub connects multiple monitors, power, and peripherals to your laptop.",
                },
                {
                    "target_sku_prefix": "TRV-UN",
                    "target_keywords": ["backpack", "bag"],
                    "score": 0.80,
                    "reason_template": "A weatherproof tech backpack securely carries your laptop, foldable stand, and tech essentials.",
                },
            ],
        },
        # 5. Desk Mat -> Mouse, Keyboard, Laptop Stand
        {
            "match_category": "Computer Accessories",
            "match_keywords": ["desk mat", "mat", "pad"],
            "complement_rules": [
                {
                    "target_sku_prefix": "ACC-PG",
                    "target_keywords": ["mouse"],
                    "score": 0.88,
                    "reason_template": "A silent ergonomic wireless mouse designed for smooth gliding on your {primary_name}.",
                },
                {
                    "target_sku_prefix": "ACC-EP",
                    "target_keywords": ["keyboard"],
                    "score": 0.85,
                    "reason_template": "A compact mechanical keyboard that rests neatly on your extended felt desk mat.",
                },
                {
                    "target_sku_prefix": "ACC-TF",
                    "target_keywords": ["laptop stand"],
                    "score": 0.80,
                    "reason_template": "An aluminum laptop stand that rests on the mat without scratching wooden desks.",
                },
            ],
        },
        # 6. Chargers -> Braided Cables, Organizer Pouch
        {
            "match_category": "Chargers & Cables",
            "match_keywords": ["charger", "gan", "power", "adapter"],
            "complement_rules": [
                {
                    "target_sku_prefix": "CHG-PA",
                    "target_keywords": ["cable", "braided"],
                    "score": 0.94,
                    "reason_template": "A 100W 5A braided USB-C cable unlocks the maximum charging wattage of your {primary_name}.",
                },
                {
                    "target_sku_prefix": "TRV-OP",
                    "target_keywords": ["organizer", "pouch"],
                    "score": 0.86,
                    "reason_template": "A shockproof travel organizer pouch keeps your {primary_name} and cords organized on the go.",
                },
            ],
        },
        # 7. Hubs & Docks -> Chargers, Cables
        {
            "match_category": "Chargers & Cables",
            "match_keywords": ["hub", "dock"],
            "complement_rules": [
                {
                    "target_sku_prefix": "CHG-VF",
                    "target_keywords": ["charger", "gan"],
                    "score": 0.90,
                    "reason_template": "Provides reliable high-wattage pass-through Power Delivery to your {primary_name} and laptop.",
                },
                {
                    "target_sku_prefix": "CHG-PA",
                    "target_keywords": ["cable", "braided"],
                    "score": 0.86,
                    "reason_template": "Heavy-duty 100W cable for linking high-speed peripherals and charging through the dock.",
                },
            ],
        },
        # 8. Cables -> Chargers, Organizers
        {
            "match_category": "Chargers & Cables",
            "match_keywords": ["cable", "braided"],
            "complement_rules": [
                {
                    "target_sku_prefix": "CHG-VF",
                    "target_keywords": ["charger", "gan"],
                    "score": 0.92,
                    "reason_template": "Pair this cable with a 65W GaN fast charger for optimal charging speeds across all devices.",
                },
                {
                    "target_sku_prefix": "TRV-OP",
                    "target_keywords": ["organizer", "pouch"],
                    "score": 0.84,
                    "reason_template": "A compact organizer pouch prevents your {primary_name} from tangling in transit.",
                },
            ],
        },
        # 9. Backpacks -> Organizer Pouch, Travel Flask, Charger
        {
            "match_category": "Work & Travel",
            "match_keywords": ["backpack", "bag"],
            "complement_rules": [
                {
                    "target_sku_prefix": "TRV-OP",
                    "target_keywords": ["organizer", "pouch"],
                    "score": 0.92,
                    "reason_template": "Fits neatly inside your {primary_name} to keep power banks, dongles, and cords organized.",
                },
                {
                    "target_sku_prefix": "TRV-HS",
                    "target_keywords": ["flask", "bottle"],
                    "score": 0.88,
                    "reason_template": "Fits in the dedicated side pocket of your {primary_name} for 24-hour insulated hydration.",
                },
                {
                    "target_sku_prefix": "CHG-VF",
                    "target_keywords": ["charger", "gan"],
                    "score": 0.80,
                    "reason_template": "A travel-friendly GaN charger to carry in your {primary_name} for all-in-one device charging.",
                },
            ],
        },
        # 10. Organizer Pouch -> Cables, Chargers
        {
            "match_category": "Work & Travel",
            "match_keywords": ["organizer", "pouch"],
            "complement_rules": [
                {
                    "target_sku_prefix": "CHG-PA",
                    "target_keywords": ["cable", "braided"],
                    "score": 0.88,
                    "reason_template": "Durable 100W braided cable designed to fit inside the elastic organizer loops.",
                },
                {
                    "target_sku_prefix": "CHG-VF",
                    "target_keywords": ["charger", "gan"],
                    "score": 0.86,
                    "reason_template": "Ultra-compact GaN charger that slots into the internal pouch compartments.",
                },
            ],
        },
        # 11. Travel Flask -> Backpack
        {
            "match_category": "Work & Travel",
            "match_keywords": ["flask", "bottle"],
            "complement_rules": [
                {
                    "target_sku_prefix": "TRV-UN",
                    "target_keywords": ["backpack", "bag"],
                    "score": 0.88,
                    "reason_template": "A weatherproof tech backpack with a dedicated pocket tailored for your {primary_name}.",
                },
            ],
        },
    ]

    @classmethod
    def _is_valid_candidate(
        cls,
        product: ProductResponse,
        intent: ShoppingIntent,
        excluded_ids: Set[str],
    ) -> bool:
        """Verifies candidate passes all hard constraints."""
        if not product.is_active:
            return False
        if product.inventory <= 0:
            return False
        if str(product.id) in excluded_ids:
            return False
        if intent.max_price is not None and product.price > intent.max_price:
            return False
        return True

    @classmethod
    def generate_cross_sell(
        cls,
        primary_product: ProductResponse,
        all_products: List[ProductResponse],
        intent: ShoppingIntent,
        excluded_ids: Set[str],
    ) -> List[GrowthRecommendationItem]:
        """
        Identifies and scores complementary cross-sell products for a given primary product.
        """
        cross_sell_items: List[GrowthRecommendationItem] = []
        primary_name_lower = primary_product.name.lower()
        primary_desc_lower = (primary_product.description or "").lower()
        primary_cat = primary_product.category or ""

        for rule in cls.CROSS_SELL_RULES:
            # Check if this rule applies to primary product
            cat_matches = (
                not rule.get("match_category")
                or rule["match_category"].lower() == primary_cat.lower()
            )
            kw_matches = any(
                kw in primary_name_lower or kw in primary_desc_lower
                for kw in rule.get("match_keywords", [])
            )

            if cat_matches and kw_matches:
                for comp_rule in rule["complement_rules"]:
                    sku_prefix = comp_rule.get("target_sku_prefix", "")
                    target_kws = comp_rule.get("target_keywords", [])

                    for candidate in all_products:
                        if not cls._is_valid_candidate(candidate, intent, excluded_ids):
                            continue

                        cand_name_lower = candidate.name.lower()
                        cand_desc_lower = (candidate.description or "").lower()

                        prefix_match = bool(
                            sku_prefix and candidate.sku.startswith(sku_prefix)
                        )
                        kw_match = any(
                            tkw in cand_name_lower or tkw in cand_desc_lower
                            for tkw in target_kws
                        )

                        if prefix_match or kw_match:
                            reason = comp_rule["reason_template"].format(
                                primary_name=primary_product.name
                            )
                            score = comp_rule["score"]

                            cross_sell_items.append(
                                GrowthRecommendationItem(
                                    type="cross_sell",
                                    product=candidate,
                                    primary_product_id=primary_product.id,
                                    primary_product_name=primary_product.name,
                                    score=score,
                                    reason=reason,
                                )
                            )
                            # Add candidate id to excluded to avoid duplicates across rules
                            excluded_ids.add(str(candidate.id))

        return cross_sell_items

    @classmethod
    def generate_upsell(
        cls,
        primary_product: ProductResponse,
        all_products: List[ProductResponse],
        intent: ShoppingIntent,
        excluded_ids: Set[str],
    ) -> List[GrowthRecommendationItem]:
        """
        Identifies and scores higher-tier upsell alternatives for a given primary product.
        """
        upsell_items: List[GrowthRecommendationItem] = []
        primary_price = primary_product.price
        primary_cat = primary_product.category or ""

        # Find candidates in the same or closely related category with higher price
        for candidate in all_products:
            if not cls._is_valid_candidate(candidate, intent, excluded_ids):
                continue

            # Must be same category
            if (candidate.category or "").lower() != primary_cat.lower():
                continue

            # Must cost more than primary product (true upsell)
            if candidate.price <= primary_price:
                continue

            price_diff = candidate.price - primary_price
            price_ratio = float(candidate.price / primary_price)

            # Reasonable price jump ceiling (e.g. <= 4.5x or under explicit budget)
            if price_ratio > 4.5 and intent.max_price is None:
                continue

            # Generate explainable specification improvement
            reason, spec_score = cls._explain_upsell_improvement(
                primary_product, candidate, price_diff
            )

            # Calculate total upsell score: base 0.70 + spec improvement (up to 0.20) + inventory (up to 0.10)
            inv_contrib = 0.10 if candidate.inventory >= 40 else 0.05
            total_score = round(min(1.0, 0.70 + spec_score + inv_contrib), 2)

            upsell_items.append(
                GrowthRecommendationItem(
                    type="upsell",
                    product=candidate,
                    primary_product_id=primary_product.id,
                    primary_product_name=primary_product.name,
                    score=total_score,
                    reason=reason,
                )
            )
            excluded_ids.add(str(candidate.id))

        return upsell_items

    @classmethod
    def _explain_upsell_improvement(
        cls,
        primary: ProductResponse,
        candidate: ProductResponse,
        price_diff: Decimal,
    ) -> Tuple[str, float]:
        """Generates a deterministic explanation highlighting the upgraded attributes."""
        prim_attrs = primary.attributes or {}
        cand_attrs = candidate.attributes or {}

        improvements = []
        spec_score = 0.10

        # Check Output / Power (e.g. Chargers)
        if "total_output" in cand_attrs and "total_output" in prim_attrs:
            improvements.append(
                f"upgraded power output ({cand_attrs['total_output']} vs {prim_attrs['total_output']})"
            )
            spec_score += 0.08
        elif "ports" in cand_attrs:
            improvements.append(f"expanded port connectivity ({cand_attrs['ports']})")
            spec_score += 0.06

        # Check Audio Features (e.g. Headphones / ANC / Battery)
        if "noise_cancellation" in cand_attrs and "noise_cancellation" not in prim_attrs:
            improvements.append("hybrid active noise cancellation (ANC)")
            spec_score += 0.09
        if "driver_size" in cand_attrs:
            improvements.append(f"{cand_attrs['driver_size']} drivers")
            spec_score += 0.04
        if "battery_life" in cand_attrs and "battery_life" in prim_attrs:
            improvements.append(
                f"extended battery life ({cand_attrs['battery_life']})"
            )
            spec_score += 0.05

        # Check Materials / Build
        if "material" in cand_attrs:
            improvements.append(f"premium build ({cand_attrs['material']})")
            spec_score += 0.04

        # Check Capacity (e.g. Backpacks / Flasks)
        if "capacity" in cand_attrs and "capacity" in prim_attrs:
            improvements.append(
                f"larger capacity ({cand_attrs['capacity']} vs {prim_attrs['capacity']})"
            )
            spec_score += 0.06

        if improvements:
            improvements_text = ", ".join(improvements[:2])
            reason = (
                f"Costs ₹{price_diff:,.0f} more but delivers {improvements_text} for a superior experience."
            )
        else:
            reason = (
                f"Higher tier alternative (costs ₹{price_diff:,.0f} more) offering enhanced performance and durability."
            )

        return reason, min(0.20, spec_score)

    @classmethod
    def generate_growth_recommendations(
        cls,
        db: Session,
        intent: ShoppingIntent,
        user_message: str,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[ProductResponse], List[GrowthRecommendationItem], List[GrowthRecommendationItem], int]:
        """
        Coordinates full growth pipeline:
        1. Discovers primary products matching customer intent.
        2. Fetches active in-stock catalog candidates.
        3. Generates ranked upsell and cross-sell recommendations.
        """
        # Step 1: Discover primary products
        primary_items, _ = recommendation_service.recommend_products(
            db=db,
            intent=intent,
            user_message=user_message,
            page=1,
            page_size=3,  # Focus on top 3 primary products for generating growth items
        )
        primary_products = [item.product for item in primary_items]

        if not primary_products:
            return [], [], [], 0

        # Step 2: Retrieve all active in-stock catalog products for candidate matching
        catalog_res = product_service.list_products(
            db=db,
            search=None,
            category=None,
            min_price=None,
            max_price=None,
            available=True,
            page=1,
            page_size=100,
        )
        all_active_products = catalog_res.items

        # Track excluded IDs to prevent recommending the primary products or duplicates
        primary_ids = {str(p.id) for p in primary_products}
        upsell_excluded = set(primary_ids)
        cross_sell_excluded = set(primary_ids)

        upsell_list: List[GrowthRecommendationItem] = []
        cross_sell_list: List[GrowthRecommendationItem] = []

        # Step 3: Generate upsell and cross-sell items for each primary product
        for primary in primary_products:
            upsells = cls.generate_upsell(
                primary_product=primary,
                all_products=all_active_products,
                intent=intent,
                excluded_ids=upsell_excluded,
            )
            upsell_list.extend(upsells)

            cross_sells = cls.generate_cross_sell(
                primary_product=primary,
                all_products=all_active_products,
                intent=intent,
                excluded_ids=cross_sell_excluded,
            )
            cross_sell_list.extend(cross_sells)

        # Deterministic Ranking: Score DESC, Price ASC, ID ASC
        upsell_list.sort(
            key=lambda x: (-x.score, x.product.price, str(x.product.id))
        )
        cross_sell_list.sort(
            key=lambda x: (-x.score, x.product.price, str(x.product.id))
        )

        total_growth = len(upsell_list) + len(cross_sell_list)

        # Apply pagination slicing if needed
        offset = (page - 1) * page_size
        paginated_upsell = upsell_list[offset : offset + page_size]
        paginated_cross_sell = cross_sell_list[offset : offset + page_size]

        return primary_products, paginated_upsell, paginated_cross_sell, total_growth


growth_service = GrowthRecommendationService()
