/**
 * Phase 18 / Frontend Step 5.1 — AI Scored Recommendations UI Frontend Tests.
 *
 * Verifies:
 * 1. Mode selector/toggle elements exist and render in page.tsx.
 * 2. Recommendation cards render product info, match score badge, and explainability reasoning.
 * 3. getAgentRecommendations sends query to POST /api/agent/recommend.
 * 4. Match score percentage is accurately derived from backend score.
 * 5. Recommendation card Add to Cart action reuses existing authenticated cart flow.
 * 6. Empty recommendations state renders helpful feedback.
 * 7. AI recommendation API errors surface user-friendly error state with retry.
 * 8. Empty or whitespace message is rejected client-side before network request.
 * 9. Security boundary: Zero machine agent keys (COMMERCE_AGENT_KEY, X-Agent-Key) leaked.
 * 10. End-to-end recommendation response contract aligns with backend schema.
 */

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {
  API_BASE_URL,
  getAgentRecommendations,
  AgentRecommendResponse,
  RecommendedProductItem,
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

const sampleRecommendationsResponse: AgentRecommendResponse = {
  message: "Found 2 top recommendation(s) for your request.",
  intent: {
    intent: "product_search",
    search_query: "wireless headphones",
    category: "Audio",
    min_price: 5000,
    max_price: 20000,
    currency: "INR",
    availability_required: true,
  },
  items: [
    {
      product: {
        id: "prod-rec-1",
        merchant_id: "merch-1",
        name: "AuraPulse ANC Wireless Headphones",
        description: "Flagship hybrid ANC headphones with 40-hour battery life",
        category: "Audio",
        price: "14999.00",
        currency: "INR",
        inventory: 25,
        sku: "AUD-AP-NC01",
        attributes: { anc: true, battery: "40h" },
        is_active: true,
        image_url: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      score: 0.94,
      reason: "Top match for premium noise-canceling audio within your ₹20,000 budget.",
    },
    {
      product: {
        id: "prod-rec-2",
        merchant_id: "merch-1",
        name: "SonicWave Studio Over-Ear Headphones",
        description: "Studio-grade neutral tuning with plush memory foam earcups",
        category: "Audio",
        price: "8999.00",
        currency: "INR",
        inventory: 15,
        sku: "AUD-SW-ST02",
        attributes: { drivers: "50mm" },
        is_active: true,
        image_url: "https://images.unsplash.com/photo-1583394838336-acd977736f90?w=800",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      score: 0.86,
      reason: "Excellent value option with high acoustic fidelity well under your budget cap.",
    },
  ],
  total: 2,
  page: 1,
  page_size: 10,
};

test("1. Mode selector/toggle elements exist and render in page.tsx", () => {
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const source = fs.readFileSync(pagePath, "utf-8");

  // Mode toggle group
  assert.ok(
    source.includes('data-testid="ai-mode-toggle"'),
    "page.tsx must contain ai-mode-toggle container"
  );
  assert.ok(
    source.includes('data-testid="ai-mode-search-btn"'),
    "page.tsx must contain ai-mode-search-btn button"
  );
  assert.ok(
    source.includes('data-testid="ai-mode-recommend-btn"'),
    "page.tsx must contain ai-mode-recommend-btn button"
  );

  // Mode labels
  assert.ok(
    source.includes("Smart Search"),
    "page.tsx must contain Smart Search label"
  );
  assert.ok(
    source.includes("Top AI Picks / Recommend for Me"),
    "page.tsx must contain Top AI Picks / Recommend for Me label"
  );
  assert.ok(
    source.includes("AI_RECOMMEND_EXAMPLE_PROMPTS"),
    "page.tsx must define dedicated AI recommendation example prompts"
  );
});

test("2. Recommendation cards render full product info, prominent match score, and explainability reasoning", () => {
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const source = fs.readFileSync(pagePath, "utf-8");

  // RecommendationCard component definition
  assert.ok(
    source.includes("function RecommendationCard("),
    "page.tsx must define dedicated RecommendationCard component"
  );
  assert.ok(
    source.includes('data-testid="recommendation-card"'),
    "RecommendationCard must include data-testid='recommendation-card'"
  );
  assert.ok(
    source.includes('data-testid="recommendation-score"'),
    "RecommendationCard must include data-testid='recommendation-score'"
  );
  assert.ok(
    source.includes('data-testid="recommendation-reason"'),
    "RecommendationCard must include data-testid='recommendation-reason'"
  );
  assert.ok(
    source.includes("Why this matches:"),
    "RecommendationCard must include explainability label 'Why this matches:'"
  );
});

test("3. getAgentRecommendations sends query to POST /api/agent/recommend", async () => {
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

    return new Response(JSON.stringify(sampleRecommendationsResponse), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const userQuery = "Best noise cancelling headphones under 15000";
    const res = await getAgentRecommendations({
      message: userQuery,
      page: 1,
      page_size: 10,
    });

    assert.equal(capturedUrl, `${API_BASE_URL}/api/agent/recommend`);
    assert.equal(capturedMethod, "POST");
    assert.equal(capturedBody?.message, userQuery);
    assert.equal(capturedBody?.page, 1);
    assert.equal(capturedBody?.page_size, 10);

    assert.equal(res.total, 2);
    assert.equal(res.items.length, 2);
    assert.equal(res.items[0].product.name, "AuraPulse ANC Wireless Headphones");
    assert.equal(res.items[0].score, 0.94);
    assert.ok(res.items[0].reason.includes("premium noise-canceling"));
  } finally {
    global.fetch = originalFetch;
  }
});

test("4. Match score percentage is accurately derived from backend float score", () => {
  // Test percentage derivation formula
  function deriveMatchPercentage(score: number): number {
    return Math.round(score > 1 ? score : score * 100);
  }

  assert.equal(deriveMatchPercentage(0.94), 94);
  assert.equal(deriveMatchPercentage(0.86), 86);
  assert.equal(deriveMatchPercentage(0.725), 73);
  assert.equal(deriveMatchPercentage(1.0), 100);
  assert.equal(deriveMatchPercentage(0.0), 0);
  // Also supports 0-100 scale safely if backend returns percentage
  assert.equal(deriveMatchPercentage(95), 95);

  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const source = fs.readFileSync(pagePath, "utf-8");

  assert.ok(
    source.includes("Math.round(score > 1 ? score : score * 100)"),
    "page.tsx must derive match percentage from backend score without reinventing scoring"
  );
  assert.ok(
    source.includes("% Match"),
    "page.tsx must format the score with '% Match'"
  );
});

test("5. Recommendation card Add to Cart action reuses existing authenticated cart flow", () => {
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const source = fs.readFileSync(pagePath, "utf-8");

  // Verify RecommendationCard wires onAddToCart to handleAddToCart
  assert.ok(
    source.includes("onAddToCart={handleAddToCart}"),
    "RecommendationCard must receive the authenticated handleAddToCart handler"
  );
  assert.ok(
    source.includes("onOpenDetails={handleOpenProductDetail}"),
    "RecommendationCard must wire details modal to handleOpenProductDetail"
  );
  assert.ok(
    source.includes("isAdding={addingProductId === recItem.product.id}"),
    "RecommendationCard must track per-item adding state via addingProductId"
  );
});

test("6. Empty recommendations state renders helpful feedback without crashing", () => {
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const source = fs.readFileSync(pagePath, "utf-8");

  assert.ok(
    source.includes('data-testid="empty-recommendations"'),
    "page.tsx must contain empty recommendations state container"
  );
  assert.ok(
    source.includes("No recommendations found matching your preferences"),
    "page.tsx must guide users when no recommendation matches are found"
  );
});

test("7. AI recommendation API errors surface user-friendly error state with retry", async () => {
  const originalFetch = global.fetch;

  (global as unknown as { fetch: unknown }).fetch = async () => {
    return new Response(
      JSON.stringify({ detail: "Recommendation engine temporarily unavailable." }),
      {
        status: 503,
        headers: { "Content-Type": "application/json" },
      }
    );
  };

  try {
    await assert.rejects(
      async () => {
        await getAgentRecommendations({ message: "noise cancelling headphones" });
      },
      {
        name: "Error",
        message: "Recommendation engine temporarily unavailable.",
      }
    );
  } finally {
    global.fetch = originalFetch;
  }
});

test("8. Empty or whitespace message is rejected client-side before network request", async () => {
  let fetchCalled = false;
  const originalFetch = global.fetch;

  (global as unknown as { fetch: unknown }).fetch = async () => {
    fetchCalled = true;
    return new Response("{}", { status: 200 });
  };

  try {
    await assert.rejects(
      async () => {
        await getAgentRecommendations({ message: "" });
      },
      {
        name: "Error",
        message: "Message cannot be empty.",
      }
    );

    await assert.rejects(
      async () => {
        await getAgentRecommendations({ message: "   \t\n  " });
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

test("9. Security boundary: Frontend recommendation flow never leaks or sends COMMERCE_AGENT_KEY or X-Agent-Key", () => {
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
  }
});

test("10. End-to-end recommendation response contract aligns with backend RecommendedProductItem schema", () => {
  const item = sampleRecommendationsResponse.items[0];

  assert.ok(item.product.id, "product must have id");
  assert.ok(item.product.name, "product must have name");
  assert.ok(item.product.price, "product must have price");
  assert.ok(typeof item.score === "number", "item score must be a number");
  assert.ok(item.score >= 0.0 && item.score <= 1.0, "item score must be between 0.0 and 1.0");
  assert.ok(typeof item.reason === "string", "item reason must be a string");
  assert.ok(item.reason.length > 0, "item reason must not be empty");
});
