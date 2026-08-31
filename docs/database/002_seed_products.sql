-- Initial Product Catalog Seed Data
-- Migration / Script: 002_seed_products.sql
-- Description: Idempotently seeds Demo Merchant and 14 Catalog Products

DO $$
DECLARE
    v_merchant_id UUID;
BEGIN
    -- 1. Insert or Retrieve Demo Merchant
    INSERT INTO merchants (id, name, description, created_at, updated_at)
    VALUES (
        gen_random_uuid(),
        'AI Commerce Demo Store',
        'Flagship showcase store for smart electronics, audio equipment, and workspace accessories built for the AI Commerce Agent platform.',
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    )
    ON CONFLICT DO NOTHING;

    SELECT id INTO v_merchant_id FROM merchants WHERE name = 'AI Commerce Demo Store' LIMIT 1;

    -- 2. Upsert Catalog Products
    -- Audio
    INSERT INTO products (id, merchant_id, name, description, category, price, currency, inventory, sku, attributes, is_active, created_at, updated_at)
    VALUES
    (
        gen_random_uuid(), v_merchant_id,
        'AuraPulse Wireless Noise-Cancelling Headphones',
        'Premium over-ear wireless headphones featuring adaptive hybrid active noise cancellation, 40mm hi-res dynamic drivers, and 45-hour battery life.',
        'Audio', 14999.00, 'INR', 45, 'AUD-AP-NC01',
        '{"brand": "AuraSound", "color": "Matte Black", "connectivity": "Bluetooth 5.3, 3.5mm Aux", "battery_life": "45 hours", "noise_cancellation": "Hybrid ANC (up to 42dB)", "driver_size": "40mm dynamic", "fast_charging": "10 mins charge = 5 hours playback", "material": "Memory foam, anodized aluminum", "weight": "250g", "tier": "flagship"}'::jsonb,
        TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    ),
    (
        gen_random_uuid(), v_merchant_id,
        'AuraSound Mini Wireless Earbuds',
        'Compact true wireless earbuds with environmental noise cancellation, IPX5 water resistance, and crystal-clear call quality.',
        'Audio', 3499.00, 'INR', 80, 'AUD-AS-EB02',
        '{"brand": "AuraSound", "color": "Pearl White", "connectivity": "Bluetooth 5.3", "battery_life": "28 hours (with case)", "water_resistance": "IPX5", "controls": "Touch controls with voice assistant support", "fast_charging": "USB-C quick charge", "tier": "entry-mid"}'::jsonb,
        TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    ),
    (
        gen_random_uuid(), v_merchant_id,
        'SonicBoom Portable Bluetooth Speaker',
        'Rugged 20W portable speaker delivering 360-degree bass-boosted sound, IP67 waterproof rating, and 16 hours of continuous playtime.',
        'Audio', 2999.00, 'INR', 60, 'AUD-SB-SP03',
        '{"brand": "SonicWave", "color": "Navy Blue", "output_power": "20W RMS", "connectivity": "Bluetooth 5.2, MicroSD, Aux", "battery_life": "16 hours", "waterproof_rating": "IP67 dust & waterproof", "tier": "budget-friendly"}'::jsonb,
        TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    ),
    -- Computer Accessories
    (
        gen_random_uuid(), v_merchant_id,
        'ErgoPro Mechanical Wireless Keyboard',
        '75% compact wireless mechanical keyboard with hot-swappable custom tactile switches, RGB backlighting, and multi-device Bluetooth/2.4GHz switching.',
        'Computer Accessories', 7999.00, 'INR', 35, 'ACC-EP-KB01',
        '{"brand": "ErgoTech", "layout": "75% ANSI (84 keys)", "switch_type": "Gateron Brown Tactile (Hot-swappable)", "connectivity": "Triple-mode (Bluetooth 5.1 / 2.4GHz / USB-C)", "backlight": "Per-key RGB (18 presets)", "battery": "4000mAh (up to 200 hours without RGB)", "compatibility": "macOS, Windows, iOS, Android", "tier": "premium"}'::jsonb,
        TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    ),
    (
        gen_random_uuid(), v_merchant_id,
        'PrecisionGlide Ergonomic Wireless Mouse',
        'Sculpted ergonomic vertical mouse with silent optical switches, hyper-fast scroll wheel, and 4000 DPI adjustable optical sensor.',
        'Computer Accessories', 2499.00, 'INR', 90, 'ACC-PG-MS02',
        '{"brand": "ErgoTech", "color": "Graphite Grey", "sensor": "High Precision Optical (800 - 4000 DPI)", "connectivity": "Bluetooth Low Energy & 2.4GHz USB Dongle", "battery_life": "Up to 70 days on full charge", "buttons": "6 programmable buttons", "tier": "mid-tier"}'::jsonb,
        TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    ),
    (
        gen_random_uuid(), v_merchant_id,
        'UltraGlide Extended Felt Desk Mat',
        'Premium 900x400mm water-repellent felt wool desk pad with anti-slip rubberized base to protect workspace surfaces.',
        'Computer Accessories', 999.00, 'INR', 120, 'ACC-UG-DM03',
        '{"brand": "DeskCraft", "dimensions": "900mm x 400mm x 4mm", "material": "High-density natural felt with natural rubber backing", "color": "Charcoal Grey", "features": "Water-resistant coating, anti-fray stitched edges", "tier": "budget-friendly"}'::jsonb,
        TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    ),
    (
        gen_random_uuid(), v_merchant_id,
        'TitanFlex Aluminum Laptop Stand',
        'Ergonomic foldable aluminum riser for laptops up to 17 inches with 6 adjustable height angles and heat dissipation ventilation.',
        'Computer Accessories', 1899.00, 'INR', 75, 'ACC-TF-LS04',
        '{"brand": "DeskCraft", "material": "Sandblasted Aviation-Grade Aluminum Alloy", "compatibility": "Laptops 10\" to 17.3\", MacBook, iPad Pro", "adjustability": "6 ergonomic viewing angles (15° to 45°)", "weight_capacity": "Up to 10kg", "foldable": true, "tier": "mid-tier"}'::jsonb,
        TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    ),
    -- Chargers & Cables
    (
        gen_random_uuid(), v_merchant_id,
        'VoltFast 65W GaN Fast Charger',
        'Ultra-compact Gallium Nitride (GaN III) dual USB-C + USB-A wall charger capable of fast-charging laptops, tablets, and phones simultaneously.',
        'Chargers & Cables', 1999.00, 'INR', 110, 'CHG-VF-65W01',
        '{"brand": "VoltTech", "total_output": "65W Max", "technology": "GaN III (Gallium Nitride)", "ports": "2x USB-C (PD 3.0 / PPS), 1x USB-A (QC 4.0)", "protection": "Over-voltage, over-current, short-circuit, thermal guard", "tier": "budget-friendly"}'::jsonb,
        TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    ),
    (
        gen_random_uuid(), v_merchant_id,
        'VoltFast 100W GaN 4-Port Desktop Charger',
        'High-power 100W desktop charging station with 3x USB-C and 1x USB-A ports, intelligent power allocation, and dedicated power cord.',
        'Chargers & Cables', 3999.00, 'INR', 50, 'CHG-VF-100W02',
        '{"brand": "VoltTech", "total_output": "100W Max", "technology": "GaN Pro Fast Charging", "ports": "3x USB-C (100W PD), 1x USB-A (22.5W QC)", "form_factor": "Desktop station with 1.5m AC power cable", "tier": "premium-upsell"}'::jsonb,
        TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    ),
    (
        gen_random_uuid(), v_merchant_id,
        'OmniLink 8-in-1 USB-C Hub & Dock',
        'Aluminum USB-C multi-port adapter with 4K@60Hz HDMI, 100W Power Delivery pass-through, Gigabit Ethernet, SD/TF card readers, and 3x USB 3.0 ports.',
        'Chargers & Cables', 3299.00, 'INR', 65, 'CHG-OL-HB03',
        '{"brand": "OmniLink", "ports": "1x HDMI (4K 60Hz), 1x USB-C PD (100W), 1x RJ45 (1000Mbps), 3x USB 3.0 (5Gbps), 1x SD, 1x TF", "material": "Space Grey Aluminum Housing", "compatibility": "MacBook M1/M2/M3, Windows laptops, iPad Pro, Steam Deck", "tier": "essential-dock"}'::jsonb,
        TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    ),
    (
        gen_random_uuid(), v_merchant_id,
        'PowerArmor Braided USB-C to USB-C Cable (2m)',
        'Heavy-duty nylon braided 100W Power Delivery 5A charging cable with reinforced E-marker chip and 480Mbps data transfer.',
        'Chargers & Cables', 599.00, 'INR', 150, 'CHG-PA-CB04',
        '{"brand": "VoltTech", "length": "2 meters (6.6 ft)", "max_power": "100W (20V / 5A)", "material": "Double-braided ballistic nylon with aluminum shell", "bend_lifespan": "30,000+ bends", "tier": "budget-cross-sell"}'::jsonb,
        TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    ),
    -- Work & Travel
    (
        gen_random_uuid(), v_merchant_id,
        'UrbanNomad Waterproof Tech Backpack (20L)',
        'Sleek weatherproof commuter backpack with dedicated 16-inch padded laptop compartment, hidden anti-theft pocket, and luggage strap.',
        'Work & Travel', 4499.00, 'INR', 40, 'TRV-UN-BP01',
        '{"brand": "NomadGear", "capacity": "20 Liters", "laptop_fit": "Up to 16-inch MacBook Pro / Gaming laptop", "material": "840D Ballistic Waterproof Nylon & YKK Zippers", "weight": "850g", "features": "TSA checkpoint-friendly, quick-access card slot, luggage pass-through", "tier": "premium-travel"}'::jsonb,
        TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    ),
    (
        gen_random_uuid(), v_merchant_id,
        'OrganizePro Compact Cable & Tech Organizer Pouch',
        'Hard-shell water-resistant travel organizer with elastic loops and mesh dividers for chargers, cables, power banks, and memory cards.',
        'Work & Travel', 1199.00, 'INR', 95, 'TRV-OP-PC02',
        '{"brand": "NomadGear", "dimensions": "24cm x 17cm x 6cm", "material": "Water-repellent Oxford fabric with shockproof EVA padding", "compartments": "2 main zipper compartments with 8 elastic slots & 4 mesh pockets", "tier": "budget-cross-sell"}'::jsonb,
        TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    ),
    (
        gen_random_uuid(), v_merchant_id,
        'HydroShield Insulated Stainless Travel Flask (750ml)',
        'Double-wall vacuum-insulated 18/8 stainless steel bottle keeping beverages cold for 24 hours or hot for 12 hours with leakproof magnetic cap.',
        'Work & Travel', 1299.00, 'INR', 70, 'TRV-HS-FL03',
        '{"brand": "NomadGear", "capacity": "750 ml", "insulation": "Double-wall vacuum insulation", "material": "Food-grade 18/8 Pro-Grade Stainless Steel (BPA Free)", "temperature_retention": "Cold: 24h, Hot: 12h", "tier": "lifestyle-accessory"}'::jsonb,
        TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    )
    ON CONFLICT (merchant_id, sku) DO UPDATE SET
        name = EXCLUDED.name,
        description = EXCLUDED.description,
        category = EXCLUDED.category,
        price = EXCLUDED.price,
        currency = EXCLUDED.currency,
        inventory = EXCLUDED.inventory,
        attributes = EXCLUDED.attributes,
        is_active = EXCLUDED.is_active,
        updated_at = CURRENT_TIMESTAMP;

END $$;
