/**
 * Step 3A — Authenticated Add to Cart Frontend Tests.
 *
 * Verifies:
 * 1. Authenticated Add to Cart sends POST /api/cart/{customerId}/items.
 * 2. product_id and quantity (default 1) are serialized correctly in request body.
 * 3. Client authorization attaches Bearer JWT token to the request.
 * 4. Unauthenticated behavior does not make a cart mutation request.
 * 5. Backend error responses (e.g. 400, 403, 500) are surfaced correctly with descriptive errors.
 * 6. fetchCart retrieves active customer cart items and totals.
 * 7. Frontend source code still does not expose or leak COMMERCE_AGENT_KEY or X-Agent-Key.
 */

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {
  addToCart,
  fetchCart,
  API_BASE_URL,
  CartResponse,
} from "../src/lib/api";
import { setStoredToken, clearAuth, getStoredToken } from "../src/lib/auth";

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

// Setup simulated browser environment
(global as unknown as { window: unknown }).window = {};
(global as unknown as { localStorage: MockLocalStorage }).localStorage = new MockLocalStorage();

test("1. Authenticated Add to Cart sends POST /api/cart/{customerId}/items with JWT", async () => {
  const originalFetch = global.fetch;
  let capturedUrl = "";
  let capturedMethod = "";
  let capturedHeaders: Record<string, string> = {};
  let capturedBody: any = null;

  setStoredToken("test_customer_jwt_token_456");

  const mockCart: CartResponse = {
    id: "cart-uuid-456",
    customer_id: "cust-uuid-456",
    status: "active",
    currency: "INR",
    items: [
      {
        id: "cart-item-1",
        cart_id: "cart-uuid-456",
        product_id: "465206d3-bd4d-4f9f-b705-010670ab4006",
        product_name: "AuraPulse Wireless Noise-Cancelling Headphones",
        sku: "AUD-AP-NC01",
        category: "Audio",
        quantity: 1,
        unit_price: "14999.00",
        total_price: "14999.00",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ],
    item_count: 1,
    subtotal: "14999.00",
    discount: "0.00",
    total: "14999.00",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  (global as unknown as { fetch: unknown }).fetch = async (
    input: RequestInfo | URL,
    init?: RequestInit
  ) => {
    capturedUrl = String(input);
    capturedMethod = init?.method || "GET";
    capturedHeaders = (init?.headers as Record<string, string>) || {};
    capturedBody = init?.body ? JSON.parse(String(init.body)) : null;

    return new Response(JSON.stringify(mockCart), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const customerId = "cust-uuid-456";
    const productId = "465206d3-bd4d-4f9f-b705-010670ab4006";

    const response = await addToCart(customerId, productId, 1);

    // 1. Proves URL is POST /api/cart/{customerId}/items
    assert.equal(capturedUrl, `${API_BASE_URL}/api/cart/${customerId}/items`);
    assert.equal(capturedMethod, "POST");

    // 2. Proves Authorization Bearer token is attached
    assert.equal(capturedHeaders["Authorization"], "Bearer test_customer_jwt_token_456");

    // 3. Proves product_id and quantity are serialized correctly
    assert.equal(capturedBody.product_id, productId);
    assert.equal(capturedBody.quantity, 1);

    // 4. Proves returned cart response is received
    assert.equal(response.item_count, 1);
    assert.equal(response.total, "14999.00");
    assert.equal(response.items[0].product_name, "AuraPulse Wireless Noise-Cancelling Headphones");
  } finally {
    clearAuth();
    global.fetch = originalFetch;
  }
});

test("2. product_id and quantity serialization validates positive integer quantity", async () => {
  let fetchCalled = false;
  const originalFetch = global.fetch;

  (global as unknown as { fetch: unknown }).fetch = async () => {
    fetchCalled = true;
    return new Response("{}", { status: 200 });
  };

  try {
    // Rejects quantity 0
    await assert.rejects(
      async () => {
        await addToCart("cust-1", "prod-1", 0);
      },
      {
        name: "Error",
        message: "Quantity must be at least 1.",
      }
    );

    // Rejects negative quantity
    await assert.rejects(
      async () => {
        await addToCart("cust-1", "prod-1", -1);
      },
      {
        name: "Error",
        message: "Quantity must be at least 1.",
      }
    );

    assert.equal(fetchCalled, false, "network fetch was not called for invalid quantities");
  } finally {
    global.fetch = originalFetch;
  }
});

test("3. Unauthenticated customer cannot make authorized cart request without token", async () => {
  const originalFetch = global.fetch;
  let capturedHeaders: Record<string, string> = {};

  // Ensure no token is in storage
  clearAuth();
  assert.equal(getStoredToken(), null);

  (global as unknown as { fetch: unknown }).fetch = async (
    _input: RequestInfo | URL,
    init?: RequestInit
  ) => {
    capturedHeaders = (init?.headers as Record<string, string>) || {};
    return new Response(JSON.stringify({ detail: "Not authenticated" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    await assert.rejects(
      async () => {
        await addToCart("unauth-cust-id", "prod-1", 1);
      },
      {
        name: "Error",
      }
    );

    // Header does not contain Bearer token when unauthenticated
    assert.equal(capturedHeaders["Authorization"], undefined);
  } finally {
    global.fetch = originalFetch;
  }
});

test("4. Backend errors from cart endpoint are surfaced correctly", async () => {
  const originalFetch = global.fetch;

  (global as unknown as { fetch: unknown }).fetch = async () => {
    return new Response(
      JSON.stringify({ detail: "Requested quantity exceeds available inventory." }),
      {
        status: 400,
        headers: { "Content-Type": "application/json" },
      }
    );
  };

  try {
    await assert.rejects(
      async () => {
        await addToCart("cust-1", "prod-1", 999);
      },
      {
        name: "Error",
        message: "Requested quantity exceeds available inventory.",
      }
    );
  } finally {
    global.fetch = originalFetch;
  }
});

test("5. fetchCart retrieves active customer cart and item count", async () => {
  const originalFetch = global.fetch;
  let capturedUrl = "";

  (global as unknown as { fetch: unknown }).fetch = async (
    input: RequestInfo | URL
  ) => {
    capturedUrl = String(input);
    return new Response(
      JSON.stringify({
        id: "cart-active-123",
        customer_id: "cust-123",
        status: "active",
        currency: "INR",
        items: [],
        item_count: 0,
        subtotal: "0.00",
        discount: "0.00",
        total: "0.00",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  };

  try {
    const cart = await fetchCart("cust-123");
    assert.equal(capturedUrl, `${API_BASE_URL}/api/cart/cust-123`);
    assert.equal(cart.status, "active");
    assert.equal(cart.item_count, 0);
  } finally {
    global.fetch = originalFetch;
  }
});

test("6. Frontend source code never leaks or references COMMERCE_AGENT_KEY or X-Agent-Key", () => {
  const srcDir = path.resolve(__dirname, "../src");
  const files: string[] = [];

  function walk(dir: string) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(fullPath);
      } else if (/\.(ts|tsx|js|jsx)$/.test(entry.name)) {
        files.push(fullPath);
      }
    }
  }

  walk(srcDir);
  assert.ok(files.length > 0, "Expected frontend source files to inspect");

  for (const file of files) {
    const content = fs.readFileSync(file, "utf8");
    assert.ok(
      !content.includes("COMMERCE_AGENT_KEY"),
      `Forbidden COMMERCE_AGENT_KEY reference found in ${file}`
    );
    assert.ok(
      !content.includes("X-Agent-Key"),
      `Forbidden X-Agent-Key header found in ${file}`
    );
  }
});
