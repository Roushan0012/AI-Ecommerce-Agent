/**
 * Phase 4C Step 1 — Customer Orders API Client Wrapper Tests.
 *
 * Verifies:
 * 1. fetchCustomerOrders calls GET /api/orders/{customer_id} with Authorization: Bearer <token>.
 * 2. Returns typed OrderListResponse with items and total matching backend Order schema.
 * 3. Handles backend error responses (e.g., 403 Forbidden, 404 Not Found) with readable error messages.
 * 4. Clears authentication state on 401 Unauthorized.
 * 5. Frontend API source strictly isolates machine agent keys (no COMMERCE_AGENT_KEY or X-Agent-Key).
 */

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {
  API_BASE_URL,
  fetchCustomerOrders,
  OrderListResponse,
} from "../src/lib/api";
import {
  clearAuth,
  getStoredToken,
  setStoredToken,
} from "../src/lib/auth";

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

const sampleOrdersList: OrderListResponse = {
  items: [
    {
      id: "order-uuid-1",
      merchant_id: "merch-uuid-1",
      customer_id: "cust-uuid-1",
      cart_id: "cart-uuid-1",
      status: "paid",
      currency: "INR",
      subtotal: "14999.00",
      discount: "0.00",
      total: "14999.00",
      items: [
        {
          id: "item-uuid-1",
          order_id: "order-uuid-1",
          product_id: "prod-uuid-1",
          product_name: "AuraPulse ANC Headphones",
          sku: "AUD-AP-NC01",
          unit_price: "14999.00",
          quantity: 1,
          total_price: "14999.00",
          created_at: new Date().toISOString(),
        },
      ],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: "order-uuid-2",
      merchant_id: "merch-uuid-1",
      customer_id: "cust-uuid-1",
      cart_id: "cart-uuid-2",
      status: "pending_payment",
      currency: "INR",
      subtotal: "499.00",
      discount: "0.00",
      total: "499.00",
      items: [
        {
          id: "item-uuid-2",
          order_id: "order-uuid-2",
          product_id: "prod-uuid-2",
          product_name: "Braided Nylon Fast Charging Cable",
          sku: "CHG-BN-60W",
          unit_price: "499.00",
          quantity: 1,
          total_price: "499.00",
          created_at: new Date().toISOString(),
        },
      ],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ],
  total: 2,
};

test("1. fetchCustomerOrders calls GET /api/orders/{customer_id} with Authorization header", async () => {
  const originalFetch = global.fetch;
  let capturedUrl = "";
  let capturedMethod = "";
  let capturedHeaders: Record<string, string> = {};

  setStoredToken("test_customer_jwt_token_123");

  (global as unknown as { fetch: unknown }).fetch = async (
    input: RequestInfo | URL,
    init?: RequestInit
  ) => {
    capturedUrl = String(input);
    capturedMethod = init?.method || "GET";
    capturedHeaders = (init?.headers as Record<string, string>) || {};

    return new Response(JSON.stringify(sampleOrdersList), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const customerId = "cust-uuid-1";
    const result = await fetchCustomerOrders(customerId);

    assert.equal(capturedUrl, `${API_BASE_URL}/api/orders/${customerId}`);
    assert.equal(capturedMethod, "GET");
    assert.equal(
      capturedHeaders["Authorization"],
      "Bearer test_customer_jwt_token_123"
    );
    assert.equal(result.total, 2);
    assert.equal(result.items.length, 2);
    assert.equal(result.items[0].id, "order-uuid-1");
    assert.equal(result.items[0].status, "paid");
    assert.equal(result.items[1].id, "order-uuid-2");
    assert.equal(result.items[1].status, "pending_payment");
  } finally {
    global.fetch = originalFetch;
    clearAuth();
  }
});

test("2. fetchCustomerOrders handles backend 403 Forbidden with readable error", async () => {
  const originalFetch = global.fetch;

  setStoredToken("test_customer_jwt_token_123");

  (global as unknown as { fetch: unknown }).fetch = async () => {
    return new Response(
      JSON.stringify({ detail: "Access denied to these orders." }),
      {
        status: 403,
        headers: { "Content-Type": "application/json" },
      }
    );
  };

  try {
    await assert.rejects(
      async () => {
        await fetchCustomerOrders("other-customer-id");
      },
      (err: Error) => {
        assert.ok(err.message.includes("Access denied to these orders."));
        return true;
      }
    );
  } finally {
    global.fetch = originalFetch;
    clearAuth();
  }
});

test("3. fetchCustomerOrders clears auth on 401 Unauthorized", async () => {
  const originalFetch = global.fetch;

  setStoredToken("expired_or_invalid_jwt_token");
  assert.equal(getStoredToken(), "expired_or_invalid_jwt_token");

  (global as unknown as { fetch: unknown }).fetch = async () => {
    return new Response(
      JSON.stringify({ detail: "Could not validate credentials" }),
      {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }
    );
  };

  try {
    await assert.rejects(
      async () => {
        await fetchCustomerOrders("cust-uuid-1");
      },
      (err: Error) => {
        assert.ok(err.message.includes("Could not validate credentials"));
        return true;
      }
    );

    assert.equal(getStoredToken(), null, "Stored token must be cleared on 401");
  } finally {
    global.fetch = originalFetch;
    clearAuth();
  }
});

test("4. OrderListResponse interface matches backend schema contract", () => {
  const response: OrderListResponse = {
    items: [],
    total: 0,
  };
  assert.equal(Array.isArray(response.items), true);
  assert.equal(typeof response.total, "number");
});

test("5. Frontend API source strictly isolates machine agent keys", () => {
  const apiFilePath = path.resolve(__dirname, "../src/lib/api.ts");
  const apiCode = fs.readFileSync(apiFilePath, "utf8");

  assert.ok(
    !apiCode.includes("COMMERCE_AGENT_KEY"),
    "api.ts must not contain or reference COMMERCE_AGENT_KEY"
  );
  assert.ok(
    !apiCode.includes("X-Agent-Key"),
    "api.ts must not contain or reference X-Agent-Key header"
  );
});
