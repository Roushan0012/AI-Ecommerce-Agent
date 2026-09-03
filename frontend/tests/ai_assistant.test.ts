/**
 * Step 2 — AI Shopping Assistant Frontend Tests.
 *
 * Verifies:
 * 1. Ask AI sends the natural-language message to POST /api/agent/search.
 * 2. Direct catalog Search still uses GET /api/products.
 * 3. Empty AI input does not make a network request.
 * 4. AI results are rendered when the API returns products.
 * 5. Backend error handling propagates readable error messages.
 * 6. Recommendation and growth endpoints connect to respective POST routes.
 */

import test from "node:test";
import assert from "node:assert/strict";
import {
  searchWithAgent,
  fetchProducts,
  getAgentRecommendations,
  getAgentGrowth,
  API_BASE_URL,
  AgentSearchResponse,
} from "../src/lib/api";

test("1. Ask AI sends the natural-language message to POST /api/agent/search", async () => {
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

    const mockResponse: AgentSearchResponse = {
      message: "Found 1 product(s) matching your request.",
      intent: {
        intent: "product_search",
        search_query: "wireless headphones",
        category: "Audio",
        min_price: null,
        max_price: 15000,
        currency: "INR",
        availability_required: true,
      },
      items: [
        {
          id: "mock-prod-1",
          merchant_id: "mock-merch-1",
          name: "AuraPulse Wireless Headphones",
          description: "Premium ANC headphones",
          category: "Audio",
          price: "14999.00",
          currency: "INR",
          inventory: 45,
          sku: "AUD-01",
          attributes: {},
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      total: 1,
      page: 1,
      page_size: 10,
    };

    return new Response(JSON.stringify(mockResponse), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const naturalLanguageQuery = "I need wireless headphones";
    const result = await searchWithAgent({
      message: naturalLanguageQuery,
      page: 1,
      page_size: 10,
    });

    // Proves Ask AI targets POST /api/agent/search with natural-language message
    assert.equal(capturedUrl, `${API_BASE_URL}/api/agent/search`);
    assert.equal(capturedMethod, "POST");
    assert.equal(capturedBody.message, naturalLanguageQuery);
    assert.equal(capturedBody.page, 1);
    assert.equal(capturedBody.page_size, 10);

    assert.equal(result.total, 1);
    assert.equal(result.message, "Found 1 product(s) matching your request.");
    assert.equal(result.intent.category, "Audio");
    assert.equal(result.items[0].name, "AuraPulse Wireless Headphones");
  } finally {
    global.fetch = originalFetch;
  }
});

test("2. Direct catalog Search still uses GET /api/products", async () => {
  const originalFetch = global.fetch;
  let capturedUrl = "";
  let capturedMethod = "";

  (global as unknown as { fetch: unknown }).fetch = async (
    input: RequestInfo | URL,
    init?: RequestInit
  ) => {
    capturedUrl = String(input);
    capturedMethod = init?.method || "GET";

    return new Response(
      JSON.stringify({
        items: [
          {
            id: "cat-prod-1",
            merchant_id: "merch-1",
            name: "ErgoPro Mechanical Wireless Keyboard",
            description: "Ergonomic mechanical keyboard",
            category: "Computer Accessories",
            price: "8999.00",
            currency: "INR",
            inventory: 30,
            sku: "KEY-01",
            attributes: {},
            is_active: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ],
        total: 1,
        page: 1,
        page_size: 12,
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  };

  try {
    const keywordQuery = "keyboard";
    const result = await fetchProducts({
      search: keywordQuery,
      page: 1,
      page_size: 12,
    });

    // Proves direct catalog search uses GET /api/products?search=...
    assert.ok(capturedUrl.startsWith(`${API_BASE_URL}/api/products?`));
    assert.ok(capturedUrl.includes("search=keyboard"));
    assert.equal(capturedMethod, "GET");
    assert.equal(result.items.length, 1);
    assert.equal(result.items[0].name, "ErgoPro Mechanical Wireless Keyboard");
  } finally {
    global.fetch = originalFetch;
  }
});

test("3. Empty AI input does not make a network request", async () => {
  let fetchCalled = false;
  const originalFetch = global.fetch;

  (global as unknown as { fetch: unknown }).fetch = async () => {
    fetchCalled = true;
    return new Response("{}", { status: 200 });
  };

  try {
    // Empty string
    await assert.rejects(
      async () => {
        await searchWithAgent({ message: "" });
      },
      {
        name: "Error",
        message: "Message cannot be empty.",
      }
    );

    // Whitespace only
    await assert.rejects(
      async () => {
        await searchWithAgent({ message: "    " });
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

test("4. AI results are rendered when the API returns products", async () => {
  const originalFetch = global.fetch;

  const mockAiResponse: AgentSearchResponse = {
    message: "I found 2 product(s) matching your request.",
    intent: {
      intent: "product_search",
      search_query: "charger",
      category: "Chargers & Cables",
      min_price: 1000,
      max_price: 3000,
      currency: "INR",
      availability_required: true,
    },
    items: [
      {
        id: "prod-charger-1",
        merchant_id: "merch-1",
        name: "VoltFast 65W GaN Fast Charger",
        description: "Compact 65W fast charger",
        category: "Chargers & Cables",
        price: "2499.00",
        currency: "INR",
        inventory: 60,
        sku: "CHG-65W",
        attributes: {},
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      {
        id: "prod-charger-2",
        merchant_id: "merch-1",
        name: "PowerArmor Braided USB-C Cable",
        description: "Durable 2m braided cable",
        category: "Chargers & Cables",
        price: "799.00",
        currency: "INR",
        inventory: 120,
        sku: "CBL-2M",
        attributes: {},
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ],
    total: 2,
    page: 1,
    page_size: 10,
  };

  (global as unknown as { fetch: unknown }).fetch = async () => {
    return new Response(JSON.stringify(mockAiResponse), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const res = await searchWithAgent({ message: "fast charger" });

    // Assert conversational response and intent are available for UI rendering
    assert.equal(res.message, "I found 2 product(s) matching your request.");
    assert.equal(res.intent.category, "Chargers & Cables");
    assert.equal(res.intent.max_price, 3000);

    // Assert all card fields are valid for rendering
    assert.equal(res.items.length, 2);
    assert.equal(res.items[0].name, "VoltFast 65W GaN Fast Charger");
    assert.equal(res.items[0].price, "2499.00");
    assert.equal(res.items[0].currency, "INR");
    assert.equal(res.items[0].inventory, 60);

    assert.equal(res.items[1].name, "PowerArmor Braided USB-C Cable");
    assert.equal(res.items[1].inventory, 120);
  } finally {
    global.fetch = originalFetch;
  }
});

test("5. AI search propagates backend errors gracefully", async () => {
  const originalFetch = global.fetch;

  (global as unknown as { fetch: unknown }).fetch = async () => {
    return new Response(
      JSON.stringify({ detail: "AI model rate limit exceeded." }),
      {
        status: 429,
        headers: { "Content-Type": "application/json" },
      }
    );
  };

  try {
    await assert.rejects(
      async () => {
        await searchWithAgent({ message: "wireless earbuds" });
      },
      {
        name: "Error",
        message: "AI model rate limit exceeded.",
      }
    );
  } finally {
    global.fetch = originalFetch;
  }
});

test("6. Recommendations and growth endpoints connect to respective POST routes", async () => {
  const originalFetch = global.fetch;
  const capturedUrls: string[] = [];

  (global as unknown as { fetch: unknown }).fetch = async (
    input: RequestInfo | URL
  ) => {
    capturedUrls.push(String(input));
    return new Response(
      JSON.stringify({
        message: "ok",
        intent: { intent: "product_search", currency: "INR", availability_required: true },
        items: [],
        primary_products: [],
        upsell: [],
        cross_sell: [],
        total: 0,
        page: 1,
        page_size: 10,
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  };

  try {
    await getAgentRecommendations({ message: "keyboard" });
    await getAgentGrowth({ message: "headphones" });

    assert.equal(capturedUrls[0], `${API_BASE_URL}/api/agent/recommend`);
    assert.equal(capturedUrls[1], `${API_BASE_URL}/api/agent/growth`);
  } finally {
    global.fetch = originalFetch;
  }
});
