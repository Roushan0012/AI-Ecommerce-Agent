"""Database catalog seed module for AI Commerce Demo Store."""

import uuid
from decimal import Decimal
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db, get_engine
from app.models import Merchant, Product

DEMO_MERCHANT_NAME = "AI Commerce Demo Store"
DEMO_MERCHANT_DESCRIPTION = (
    "Flagship showcase store for smart electronics, audio equipment, "
    "and workspace accessories built for the AI Commerce Agent platform."
)

CATALOG_PRODUCTS: List[Dict[str, Any]] = [
    # 1. Audio Category
    {
        "name": "AuraPulse Wireless Noise-Cancelling Headphones",
        "description": "Premium over-ear wireless headphones featuring adaptive hybrid active noise cancellation, 40mm hi-res dynamic drivers, and 45-hour battery life.",
        "category": "Audio",
        "price": Decimal("14999.00"),
        "currency": "INR",
        "inventory": 45,
        "sku": "AUD-AP-NC01",
        "attributes": {
            "brand": "AuraSound",
            "color": "Matte Black",
            "connectivity": "Bluetooth 5.3, 3.5mm Aux",
            "battery_life": "45 hours",
            "noise_cancellation": "Hybrid ANC (up to 42dB)",
            "driver_size": "40mm dynamic",
            "fast_charging": "10 mins charge = 5 hours playback",
            "material": "Memory foam, anodized aluminum",
            "weight": "250g",
            "tier": "flagship",
        },
        "is_active": True,
    },
    {
        "name": "AuraSound Mini Wireless Earbuds",
        "description": "Compact true wireless earbuds with environmental noise cancellation, IPX5 water resistance, and crystal-clear call quality.",
        "category": "Audio",
        "price": Decimal("3499.00"),
        "currency": "INR",
        "inventory": 80,
        "sku": "AUD-AS-EB02",
        "attributes": {
            "brand": "AuraSound",
            "color": "Pearl White",
            "connectivity": "Bluetooth 5.3",
            "battery_life": "28 hours (with case)",
            "water_resistance": "IPX5",
            "controls": "Touch controls with voice assistant support",
            "fast_charging": "USB-C quick charge",
            "tier": "entry-mid",
        },
        "is_active": True,
    },
    {
        "name": "SonicBoom Portable Bluetooth Speaker",
        "description": "Rugged 20W portable speaker delivering 360-degree bass-boosted sound, IP67 waterproof rating, and 16 hours of continuous playtime.",
        "category": "Audio",
        "price": Decimal("2999.00"),
        "currency": "INR",
        "inventory": 60,
        "sku": "AUD-SB-SP03",
        "attributes": {
            "brand": "SonicWave",
            "color": "Navy Blue",
            "output_power": "20W RMS",
            "connectivity": "Bluetooth 5.2, MicroSD, Aux",
            "battery_life": "16 hours",
            "waterproof_rating": "IP67 dust & waterproof",
            "tier": "budget-friendly",
        },
        "is_active": True,
    },

    # 2. Computer Accessories
    {
        "name": "ErgoPro Mechanical Wireless Keyboard",
        "description": "75% compact wireless mechanical keyboard with hot-swappable custom tactile switches, RGB backlighting, and multi-device Bluetooth/2.4GHz switching.",
        "category": "Computer Accessories",
        "price": Decimal("7999.00"),
        "currency": "INR",
        "inventory": 35,
        "sku": "ACC-EP-KB01",
        "attributes": {
            "brand": "ErgoTech",
            "layout": "75% ANSI (84 keys)",
            "switch_type": "Gateron Brown Tactile (Hot-swappable)",
            "connectivity": "Triple-mode (Bluetooth 5.1 / 2.4GHz / USB-C)",
            "backlight": "Per-key RGB (18 presets)",
            "battery": "4000mAh (up to 200 hours without RGB)",
            "compatibility": "macOS, Windows, iOS, Android",
            "tier": "premium",
        },
        "is_active": True,
    },
    {
        "name": "PrecisionGlide Ergonomic Wireless Mouse",
        "description": "Sculpted ergonomic vertical mouse with silent optical switches, hyper-fast scroll wheel, and 4000 DPI adjustable optical sensor.",
        "category": "Computer Accessories",
        "price": Decimal("2499.00"),
        "currency": "INR",
        "inventory": 90,
        "sku": "ACC-PG-MS02",
        "attributes": {
            "brand": "ErgoTech",
            "color": "Graphite Grey",
            "sensor": "High Precision Optical (800 - 4000 DPI)",
            "connectivity": "Bluetooth Low Energy & 2.4GHz USB Dongle",
            "battery_life": "Up to 70 days on full charge",
            "buttons": "6 programmable buttons",
            "tier": "mid-tier",
        },
        "is_active": True,
    },
    {
        "name": "UltraGlide Extended Felt Desk Mat",
        "description": "Premium 900x400mm water-repellent felt wool desk pad with anti-slip rubberized base to protect workspace surfaces.",
        "category": "Computer Accessories",
        "price": Decimal("999.00"),
        "currency": "INR",
        "inventory": 120,
        "sku": "ACC-UG-DM03",
        "attributes": {
            "brand": "DeskCraft",
            "dimensions": "900mm x 400mm x 4mm",
            "material": "High-density natural felt with natural rubber backing",
            "color": "Charcoal Grey",
            "features": "Water-resistant coating, anti-fray stitched edges",
            "tier": "budget-friendly",
        },
        "is_active": True,
    },
    {
        "name": "TitanFlex Aluminum Laptop Stand",
        "description": "Ergonomic foldable aluminum riser for laptops up to 17 inches with 6 adjustable height angles and heat dissipation ventilation.",
        "category": "Computer Accessories",
        "price": Decimal("1899.00"),
        "currency": "INR",
        "inventory": 75,
        "sku": "ACC-TF-LS04",
        "attributes": {
            "brand": "DeskCraft",
            "material": "Sandblasted Aviation-Grade Aluminum Alloy",
            "compatibility": "Laptops 10\" to 17.3\", MacBook, iPad Pro",
            "adjustability": "6 ergonomic viewing angles (15° to 45°)",
            "weight_capacity": "Up to 10kg",
            "foldable": True,
            "tier": "mid-tier",
        },
        "is_active": True,
    },

    # 3. Chargers & Cables
    {
        "name": "VoltFast 65W GaN Fast Charger",
        "description": "Ultra-compact Gallium Nitride (GaN III) dual USB-C + USB-A wall charger capable of fast-charging laptops, tablets, and phones simultaneously.",
        "category": "Chargers & Cables",
        "price": Decimal("1999.00"),
        "currency": "INR",
        "inventory": 110,
        "sku": "CHG-VF-65W01",
        "attributes": {
            "brand": "VoltTech",
            "total_output": "65W Max",
            "technology": "GaN III (Gallium Nitride)",
            "ports": "2x USB-C (PD 3.0 / PPS), 1x USB-A (QC 4.0)",
            "protection": "Over-voltage, over-current, short-circuit, thermal guard",
            "tier": "budget-friendly",
        },
        "is_active": True,
    },
    {
        "name": "VoltFast 100W GaN 4-Port Desktop Charger",
        "description": "High-power 100W desktop charging station with 3x USB-C and 1x USB-A ports, intelligent power allocation, and dedicated power cord.",
        "category": "Chargers & Cables",
        "price": Decimal("3999.00"),
        "currency": "INR",
        "inventory": 50,
        "sku": "CHG-VF-100W02",
        "attributes": {
            "brand": "VoltTech",
            "total_output": "100W Max",
            "technology": "GaN Pro Fast Charging",
            "ports": "3x USB-C (100W PD), 1x USB-A (22.5W QC)",
            "form_factor": "Desktop station with 1.5m AC power cable",
            "tier": "premium-upsell",
        },
        "is_active": True,
    },
    {
        "name": "OmniLink 8-in-1 USB-C Hub & Dock",
        "description": "Aluminum USB-C multi-port adapter with 4K@60Hz HDMI, 100W Power Delivery pass-through, Gigabit Ethernet, SD/TF card readers, and 3x USB 3.0 ports.",
        "category": "Chargers & Cables",
        "price": Decimal("3299.00"),
        "currency": "INR",
        "inventory": 65,
        "sku": "CHG-OL-HB03",
        "attributes": {
            "brand": "OmniLink",
            "ports": "1x HDMI (4K 60Hz), 1x USB-C PD (100W), 1x RJ45 (1000Mbps), 3x USB 3.0 (5Gbps), 1x SD, 1x TF",
            "material": "Space Grey Aluminum Housing",
            "compatibility": "MacBook M1/M2/M3, Windows laptops, iPad Pro, Steam Deck",
            "tier": "essential-dock",
        },
        "is_active": True,
    },
    {
        "name": "PowerArmor Braided USB-C to USB-C Cable (2m)",
        "description": "Heavy-duty nylon braided 100W Power Delivery 5A charging cable with reinforced E-marker chip and 480Mbps data transfer.",
        "category": "Chargers & Cables",
        "price": Decimal("599.00"),
        "currency": "INR",
        "inventory": 150,
        "sku": "CHG-PA-CB04",
        "attributes": {
            "brand": "VoltTech",
            "length": "2 meters (6.6 ft)",
            "max_power": "100W (20V / 5A)",
            "material": "Double-braided ballistic nylon with aluminum shell",
            "bend_lifespan": "30,000+ bends",
            "tier": "budget-cross-sell",
        },
        "is_active": True,
    },

    # 4. Work & Travel
    {
        "name": "UrbanNomad Waterproof Tech Backpack (20L)",
        "description": "Sleek weatherproof commuter backpack with dedicated 16-inch padded laptop compartment, hidden anti-theft pocket, and luggage strap.",
        "category": "Work & Travel",
        "price": Decimal("4499.00"),
        "currency": "INR",
        "inventory": 40,
        "sku": "TRV-UN-BP01",
        "attributes": {
            "brand": "NomadGear",
            "capacity": "20 Liters",
            "laptop_fit": "Up to 16-inch MacBook Pro / Gaming laptop",
            "material": "840D Ballistic Waterproof Nylon & YKK Zippers",
            "weight": "850g",
            "features": "TSA checkpoint-friendly, quick-access card slot, luggage pass-through",
            "tier": "premium-travel",
        },
        "is_active": True,
    },
    {
        "name": "OrganizePro Compact Cable & Tech Organizer Pouch",
        "description": "Hard-shell water-resistant travel organizer with elastic loops and mesh dividers for chargers, cables, power banks, and memory cards.",
        "category": "Work & Travel",
        "price": Decimal("1199.00"),
        "currency": "INR",
        "inventory": 95,
        "sku": "TRV-OP-PC02",
        "attributes": {
            "brand": "NomadGear",
            "dimensions": "24cm x 17cm x 6cm",
            "material": "Water-repellent Oxford fabric with shockproof EVA padding",
            "compartments": "2 main zipper compartments with 8 elastic slots & 4 mesh pockets",
            "tier": "budget-cross-sell",
        },
        "is_active": True,
    },
    {
        "name": "HydroShield Insulated Stainless Travel Flask (750ml)",
        "description": "Double-wall vacuum-insulated 18/8 stainless steel bottle keeping beverages cold for 24 hours or hot for 12 hours with leakproof magnetic cap.",
        "category": "Work & Travel",
        "price": Decimal("1299.00"),
        "currency": "INR",
        "inventory": 70,
        "sku": "TRV-HS-FL03",
        "attributes": {
            "brand": "NomadGear",
            "capacity": "750 ml",
            "insulation": "Double-wall vacuum insulation",
            "material": "Food-grade 18/8 Pro-Grade Stainless Steel (BPA Free)",
            "temperature_retention": "Cold: 24h, Hot: 12h",
            "tier": "lifestyle-accessory",
        },
        "is_active": True,
    },
]


def seed_catalog(session: Session) -> Dict[str, Any]:
    """
    Idempotently seeds the demo merchant and product catalog into the database.
    """
    # 1. Find or create demo merchant
    stmt = select(Merchant).where(Merchant.name == DEMO_MERCHANT_NAME)
    merchant = session.execute(stmt).scalar_one_or_none()

    merchant_created = False
    if not merchant:
        merchant = Merchant(
            id=uuid.uuid4(),
            name=DEMO_MERCHANT_NAME,
            description=DEMO_MERCHANT_DESCRIPTION,
        )
        session.add(merchant)
        session.flush()
        merchant_created = True

    # 2. Seed products idempotently per SKU
    products_created = 0
    products_updated = 0

    for item_data in CATALOG_PRODUCTS:
        sku = item_data["sku"]
        prod_stmt = select(Product).where(
            Product.merchant_id == merchant.id,
            Product.sku == sku,
        )
        existing_prod = session.execute(prod_stmt).scalar_one_or_none()

        if existing_prod:
            # Update attributes / inventory if changed
            existing_prod.name = item_data["name"]
            existing_prod.description = item_data["description"]
            existing_prod.category = item_data["category"]
            existing_prod.price = item_data["price"]
            existing_prod.currency = item_data["currency"]
            existing_prod.inventory = item_data["inventory"]
            existing_prod.attributes = item_data["attributes"]
            existing_prod.is_active = item_data["is_active"]
            products_updated += 1
        else:
            new_prod = Product(
                id=uuid.uuid4(),
                merchant_id=merchant.id,
                name=item_data["name"],
                description=item_data["description"],
                category=item_data["category"],
                price=item_data["price"],
                currency=item_data["currency"],
                inventory=item_data["inventory"],
                sku=sku,
                attributes=item_data["attributes"],
                is_active=item_data["is_active"],
            )
            session.add(new_prod)
            products_created += 1

    session.commit()

    # Query total products for the merchant
    total_stmt = select(Product).where(Product.merchant_id == merchant.id)
    total_products = len(session.execute(total_stmt).scalars().all())

    return {
        "merchant_id": str(merchant.id),
        "merchant_name": merchant.name,
        "merchant_created": merchant_created,
        "products_created": products_created,
        "products_updated": products_updated,
        "total_products": total_products,
    }


def main():
    engine = get_engine()
    with Session(engine) as session:
        result = seed_catalog(session)
        print("=== Database Seed Completed ===")
        print(f"Merchant: {result['merchant_name']} (ID: {result['merchant_id']})")
        print(f"Merchant Created: {result['merchant_created']}")
        print(f"Products Created: {result['products_created']}")
        print(f"Products Updated: {result['products_updated']}")
        print(f"Total Merchant Products: {result['total_products']}")


if __name__ == "__main__":
    main()
