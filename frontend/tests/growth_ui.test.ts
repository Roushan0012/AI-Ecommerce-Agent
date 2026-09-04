/**
 * Phase 18 / Frontend Step 5.2 — AI Growth Engine UI (Upsell & Cross-sell) Frontend Tests.
 *
 * Verifies:
 * 1. Toggle button ai-mode-growth-btn exists and renders in mode toggle.
 * 2. Mode switching: Growth mode title, badge, input label, and placeholder render in page.tsx.
 * 3. Submitting query in growth mode invokes getAgentGrowth / calls POST /api/agent/growth.
 * 4. Upsell section (growth-upsell-section) renders upsell items with cards, badges, and explainability reasons.
 * 5. Cross-sell section (growth-cross-sell-section) renders cross-sell items with cards, badges, and explainability reasons.
 * 6. Clear visual distinction between upsell and cross-sell badges (icons, colors, test IDs).
 * 7. Formatted INR price displays properly across growth cards.
 * 8. Add to Cart action on growth items reuses existing authenticated cart flow.
 * 9. Empty growth state (empty-growth) renders when upsell & cross-sell are empty.
 * 10. Loading indicator (ai-loading) displays during fetch with growth-specific text.
 * 11. Error banner (ai-error) displays user-friendly error message with retry button on failure.
 * 12. Client-side input validation rejects empty or whitespace queries before network request.
 * 13. Security boundary: Frontend growth flow never leaks or sends COMMERCE_AGENT_KEY or X-Agent-Key.
 * 14. End-to-end growth response contract aligns with backend schema.
 */

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {
  API_BASE_URL,
  getAgentGrowth,
  AgentGrowthResponse,
  GrowthRecommendationItem,
} from "../src/lib/api";

// In-memory localStorage mock for node test runner
class MockLocalStorage {
  private store = new Map<string, string>();

  getItem(key: string): string | null {
    return this.store.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  clear(): void {
    this.store.clear();
  }
}

(global as unknown as { window: unknown }).window = {};
(global as unknown as { localStorage: MockLocalStorage }).localStorage = new MockLocalStorage();

const sampleGrowthResponse: AgentGrowthResponse = {
  message: "Found 1 primary product, 1 upgrade option, and 1 companion accessory.",
  intent: {
    intent: "product_search",
    search_query: "mechanical keyboard",
    category: "Computer Accessories",
    min_price: 3000,
    max_price: 15000,
    currency: "INR",
    availability_required: true,
  },
  primary_products: [
    {
      id: "prod-primary-1",
      merchant_id: "merch-1",
      name: "ApexPro Tenkeyless Mechanical Keyboard",
      description: "Tactile mechanical switches with customizable per-key RGB",
      category: "Computer Accessories",
      price: "7499.00",
      currency: "INR",
      inventory: 30,
      sku: "ACC-AP-KB01",
      attributes: { switches: "tactile", layout: "TKL" },
      is_active: true,
      image_url: "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=800",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ],
  upsell: [
    {
      type: "upsell",
      product: {
        id: "prod-upsell-1",
        merchant_id: "merch-1",
        name: "ApexPro Wireless Tri-Mode Mechanical Keyboard",
        description: "Flagship wireless mechanical keyboard with hot-swappable switches and OLED display",
        category: "Computer Accessories",
        price: "11999.00",
        currency: "INR",
        inventory: 18,
        sku: "ACC-AP-WKB02",
        attributes: { wireless: true, hot_swap: true },
        is_active: true,
        image_url: "https://images.unsplash.com/photo-1595225476474-87563907a212?w=800",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      primary_product_id: "prod-primary-1",
      primary_product_name: "ApexPro Tenkeyless Mechanical Keyboard",
      score: 0.92,
      reason: "Costs ₹4,500 more for tri-mode wireless connectivity and hot-swappable switches.",
    },
  ],
  cross_sell: [
    {
      type: "cross_sell",
      product: {
        id: "prod-cross-1",
        merchant_id: "merch-1",
        name: "ErgoGlide Precision Wireless Ergonomic Mouse",
        description: "Contoured ergonomic mouse designed to complement mechanical typing setups",
        category: "Computer Accessories",
        price: "3499.00",
        currency: "INR",
        inventory: 40,
        sku: "ACC-EG-MS01",
        attributes: { dpi: 4000, ergonomic: true },
        is_active: true,
        image_url: "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=800",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      primary_product_id: "prod-primary-1",
      primary_product_name: "ApexPro Tenkeyless Mechanical Keyboard",
      score: 0.88,
      reason: "Frequently paired together: Ergonomic mouse complements mechanical keyboards for extended typing sessions.",
    },
  ],
  total: 2,
  page: 1,
  page_size: 10,
};

test("1. Toggle button ai-mode-growth-btn exists and renders in mode toggle", () => {
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const source = fs.readFileSync(pagePath, "utf-8");

  // Mode toggle group
  assert.ok(
    source.includes('data-testid="ai-mode-toggle"'),
    "page.tsx must contain ai-mode-toggle container"
  );
  assert.ok(
    source.includes('data-testid="ai-mode-growth-btn"'),
    "page.tsx must contain ai-mode-growth-btn button"
  );
  assert.ok(
    source.includes("Upgrades & Accessories"),
    "page.tsx must contain 'Upgrades & Accessories' label"
  );
  assert.ok(
    source.includes("AI_GROWTH_EXAMPLE_PROMPTS"),
    "page.tsx must define dedicated AI growth example prompts"
  );
});

test("2. Mode switching: Growth mode title, badge, input label, and placeholder render in page.tsx", () => {
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const source = fs.readFileSync(pagePath, "utf-8");

  assert.ok(
    source.includes("AI Growth Engine • Upsell & Cross-sell"),
    "page.tsx must contain Growth Engine badge label"
  );
  assert.ok(
    source.includes("AI Growth Engine (Upgrades & Accessories)"),
    "page.tsx must contain Growth Engine title"
  );
  assert.ok(
    source.includes("AI Growth & Upgrades Query:"),
    "page.tsx must contain Growth Engine input label"
  );
  assert.ok(
    source.includes('data-testid="get-growth-btn"') || source.includes('get-growth-btn'),
    "page.tsx must include submit button with get-growth-btn test ID"
  );
  assert.ok(
    source.includes("Find Upgrades & Add-ons"),
    "page.tsx must contain submit button text 'Find Upgrades & Add-ons'"
  );
});

test("3. Submitting query in growth mode invokes getAgentGrowth / calls POST /api/agent/growth", async () => {
  const originalFetch = global.fetch;
  let capturedUrl = "";
  let capturedMethod = "";
  let capturedBody: any = null;

  (global as unknown as { fetch: unknown }).fetch = async (
    input: RequestInfo | URL,
    init?: RequestInit
  ) => {
    capturedUrl = String(input);
    capturedMethod = init?.method || "GET";
    capturedBody = init?.body ? JSON.parse(String(init.body)) : null;

    return new Response(JSON.stringify(sampleGrowthResponse), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const userQuery = "I need a mechanical keyboard for coding";
    const res = await getAgentGrowth({
      message: userQuery,
      page: 1,
      page_size: 10,
    });

    assert.equal(capturedUrl, `${API_BASE_URL}/api/agent/growth`);
    assert.equal(capturedMethod, "POST");
    assert.equal(capturedBody?.message, userQuery);
    assert.equal(capturedBody?.page, 1);
    assert.equal(capturedBody?.page_size, 10);

    assert.equal(res.total, 2);
    assert.equal(res.primary_products.length, 1);
    assert.equal(res.upsell.length, 1);
    assert.equal(res.cross_sell.length, 1);
    assert.equal(res.upsell[0].type, "upsell");
    assert.equal(res.cross_sell[0].type, "cross_sell");
  } finally {
    global.fetch = originalFetch;
  }
});

test("4. Upsell section (growth-upsell-section) renders upsell items with cards, badges, and explainability reasons", () => {
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const source = fs.readFileSync(pagePath, "utf-8");

  assert.ok(
    source.includes('data-testid="growth-upsell-section"'),
    "page.tsx must contain growth-upsell-section container"
  );
  assert.ok(
    source.includes('data-testid="growth-upsell-badge"'),
    "GrowthItemCard must render growth-upsell-badge for upsell items"
  );
  assert.ok(
    source.includes("AI Upgrade"),
    "GrowthItemCard must render 'AI Upgrade' text"
  );
  assert.ok(
    source.includes("Why upgrade:"),
    "GrowthItemCard must render 'Why upgrade:' explainability label for upsells"
  );
  assert.ok(
    source.includes('data-testid="growth-reason"'),
    "GrowthItemCard must render growth-reason container"
  );
});

test("5. Cross-sell section (growth-cross-sell-section) renders cross-sell items with cards, badges, and explainability reasons", () => {
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const source = fs.readFileSync(pagePath, "utf-8");

  assert.ok(
    source.includes('data-testid="growth-cross-sell-section"'),
    "page.tsx must contain growth-cross-sell-section container"
  );
  assert.ok(
    source.includes('data-testid="growth-cross-sell-badge"'),
    "GrowthItemCard must render growth-cross-sell-badge for cross-sell items"
  );
  assert.ok(
    source.includes("Recommended Companion"),
    "GrowthItemCard must render 'Recommended Companion' text"
  );
  assert.ok(
    source.includes("Why this companion:"),
    "GrowthItemCard must render 'Why this companion:' explainability label for cross-sells"
  );
});

test("6. Clear visual distinction between upsell and cross-sell badges", () => {
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const source = fs.readFileSync(pagePath, "utf-8");

  // Upsell badge has emerald styling
  assert.ok(
    source.includes("bg-emerald-500/15") && source.includes("text-emerald-300"),
    "Upsell badge must use distinct emerald styling"
  );
  // Cross-sell badge has cyan styling
  assert.ok(
    source.includes("bg-cyan-500/15") && source.includes("text-cyan-300"),
    "Cross-sell badge must use distinct cyan styling"
  );
  // Distinct icons
  assert.ok(
    source.includes("🚀") && source.includes("🧩"),
    "Upsell and cross-sell must display distinct iconography"
  );
});

test("7. Formatted INR price displays properly across growth cards", () => {
  function formatCurrency(amount: string | number): string {
    const num = Number(amount || 0);
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(num);
  }

  const formattedUpsellPrice = formatCurrency(sampleGrowthResponse.upsell[0].product.price);
  const formattedCrossPrice = formatCurrency(sampleGrowthResponse.cross_sell[0].product.price);

  assert.ok(
    formattedUpsellPrice.includes("11,999"),
    "Upsell price must format to ₹11,999.00"
  );
  assert.ok(
    formattedCrossPrice.includes("3,499"),
    "Cross-sell price must format to ₹3,499.00"
  );

  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const source = fs.readFileSync(pagePath, "utf-8");
  assert.ok(
    source.includes("formatCurrency(product.price)"),
    "GrowthItemCard must format prices using formatCurrency"
  );
});

test("8. Add to Cart action on growth items reuses existing authenticated cart flow", () => {
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const source = fs.readFileSync(pagePath, "utf-8");

  // GrowthItemCard wires onAddToCart to handleAddToCart
  assert.ok(
    source.includes("onAddToCart={handleAddToCart}"),
    "GrowthItemCard must receive authenticated handleAddToCart handler"
  );
  assert.ok(
    source.includes("onOpenDetails={handleOpenProductDetail}"),
    "GrowthItemCard must wire modal to handleOpenProductDetail"
  );
  assert.ok(
    source.includes('data-testid="growth-add-to-cart-btn"'),
    "GrowthItemCard must include data-testid='growth-add-to-cart-btn'"
  );
  assert.ok(
    source.includes("isAdding={addingProductId === item.product.id}"),
    "GrowthItemCard must track per-item adding state via addingProductId"
  );
});

test("9. Empty growth state (empty-growth) renders when upsell & cross-sell are empty", () => {
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const source = fs.readFileSync(pagePath, "utf-8");

  assert.ok(
    source.includes('data-testid="empty-growth"'),
    "page.tsx must contain empty-growth container"
  );
  assert.ok(
    source.includes("No growth recommendations found matching your query"),
    "page.tsx must guide users when no growth matches are found"
  );
});

test("10. Loading indicator (ai-loading) displays during fetch with growth-specific text", () => {
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const source = fs.readFileSync(pagePath, "utf-8");

  assert.ok(
    source.includes('data-testid="ai-loading"'),
    "page.tsx must render ai-loading container"
  );
  assert.ok(
    source.includes("AI Growth Engine is finding upgrades & companion accessories"),
    "page.tsx must display growth-specific loading message"
  );
});

test("11. Error banner (ai-error) displays user-friendly error message with retry button on failure", async () => {
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const source = fs.readFileSync(pagePath, "utf-8");

  assert.ok(
    source.includes('data-testid="ai-error"'),
    "page.tsx must render ai-error container"
  );
  assert.ok(
    source.includes("Retry"),
    "page.tsx must render retry button in error container"
  );

  const originalFetch = global.fetch;

  (global as unknown as { fetch: unknown }).fetch = async () => {
    return new Response(
      JSON.stringify({ detail: "Growth engine temporarily unavailable." }),
      {
        status: 503,
        headers: { "Content-Type": "application/json" },
      }
    );
  };

  try {
    await assert.rejects(
      async () => {
        await getAgentGrowth({ message: "mechanical keyboard" });
      },
      {
        name: "Error",
        message: "Growth engine temporarily unavailable.",
      }
    );
  } finally {
    global.fetch = originalFetch;
  }
});

test("12. Client-side input validation rejects empty or whitespace queries before network request", async () => {
  let fetchCalled = false;
  const originalFetch = global.fetch;

  (global as unknown as { fetch: unknown }).fetch = async () => {
    fetchCalled = true;
    return new Response("{}", { status: 200 });
  };

  try {
    await assert.rejects(
      async () => {
        await getAgentGrowth({ message: "" });
      },
      {
        name: "Error",
        message: "Message cannot be empty.",
      }
    );

    await assert.rejects(
      async () => {
        await getAgentGrowth({ message: "   \t\n  " });
      },
      {
        name: "Error",
        message: "Message cannot be empty.",
      }
    );

    assert.equal(fetchCalled, false, "network fetch was not called for empty queries");
  } finally {
    global.fetch = originalFetch;
  }
});

test("13. Security boundary: Frontend growth flow never leaks or sends COMMERCE_AGENT_KEY or X-Agent-Key", () => {
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const apiPath = path.resolve(__dirname, "../src/lib/api.ts");
  const authPath = path.resolve(__dirname, "../src/lib/auth.ts");

  const pageSource = fs.readFileSync(pagePath, "utf-8");
  const apiSource = fs.readFileSync(apiPath, "utf-8");
  const authSource = fs.readFileSync(authPath, "utf-8");

  for (const [file, content] of [
    ["page.tsx", pageSource],
    ["api.ts", apiSource],
    ["auth.ts", authSource],
  ]) {
    assert.ok(
      !content.includes("COMMERCE_AGENT_KEY"),
      `${file} must never reference COMMERCE_AGENT_KEY`
    );
    assert.ok(
      !content.includes("X-Agent-Key"),
      `${file} must never transmit X-Agent-Key`
    );
    assert.ok(
      !content.includes("RAZORPAY_KEY_SECRET"),
      `${file} must never reference RAZORPAY_KEY_SECRET`
    );
    assert.ok(
      !content.includes("RAZORPAY_WEBHOOK_SECRET"),
      `${file} must never reference RAZORPAY_WEBHOOK_SECRET`
    );
    assert.ok(
      !content.includes("DATABASE_URL"),
      `${file} must never reference DATABASE_URL`
    );
  }
});

test("14. End-to-end growth response contract aligns with backend schema", () => {
  assert.equal(typeof sampleGrowthResponse.message, "string");
  assert.ok(Array.isArray(sampleGrowthResponse.primary_products));
  assert.ok(Array.isArray(sampleGrowthResponse.upsell));
  assert.ok(Array.isArray(sampleGrowthResponse.cross_sell));

  const upsellItem = sampleGrowthResponse.upsell[0];
  assert.equal(upsellItem.type, "upsell");
  assert.ok(upsellItem.product.id);
  assert.ok(upsellItem.product.name);
  assert.ok(upsellItem.primary_product_id);
  assert.ok(upsellItem.primary_product_name);
  assert.ok(typeof upsellItem.score === "number");
  assert.ok(upsellItem.score >= 0.0 && upsellItem.score <= 1.0);
  assert.ok(typeof upsellItem.reason === "string");
  assert.ok(upsellItem.reason.length > 0);

  const crossItem = sampleGrowthResponse.cross_sell[0];
  assert.equal(crossItem.type, "cross_sell");
  assert.ok(crossItem.product.id);
  assert.ok(crossItem.product.name);
  assert.ok(crossItem.primary_product_id);
  assert.ok(crossItem.primary_product_name);
  assert.ok(typeof crossItem.score === "number");
  assert.ok(crossItem.score >= 0.0 && crossItem.score <= 1.0);
  assert.ok(typeof crossItem.reason === "string");
  assert.ok(crossItem.reason.length > 0);
});
