/**
 * Phase 4C Step 2 — Customer Order History UI Frontend Tests.
 *
 * Verifies:
 * 1. Accessible 'My Orders' trigger button exists in authenticated header section.
 * 2. Order History modal markup renders with proper dialog role and accessibility labels.
 * 3. Successful order retrieval displays order summaries (ID, date, status, item count, total).
 * 4. Empty order state displays helpful guidance and catalog navigation.
 * 5. Order status badges properly reflect authoritative status (paid, pending_payment, cancelled).
 * 6. Order detail drill-down retrieves authoritative itemized receipt via fetchOrderDetail.
 * 7. Order detail back button returns user to order list.
 * 8. Loading and error states exist for both order list and order detail retrieval.
 * 9. Unauthenticated access guard renders sign-in guidance without querying backend orders.
 * 10. Checkout confirmation modal includes 'View Order History' action.
 * 11. Customer ownership boundary enforced and zero machine keys (COMMERCE_AGENT_KEY, X-Agent-Key) leaked.
 */

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {
  API_BASE_URL,
  fetchCustomerOrders,
  fetchOrderDetail,
  OrderListResponse,
  OrderResponse,
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

const sampleCustomerOrders: OrderListResponse = {
  items: [
    {
      id: "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
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
          id: "item-1",
          order_id: "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
          product_id: "prod-1",
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
      id: "e4e04cd6-fb8a-49e2-65c7-0e9d2f344815",
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
          id: "item-2",
          order_id: "e4e04cd6-fb8a-49e2-65c7-0e9d2f344815",
          product_id: "prod-2",
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

const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
const pageSource = fs.readFileSync(pagePath, "utf8");

test("1. Accessible 'My Orders' trigger button exists in authenticated header section", () => {
  assert.ok(
    pageSource.includes('data-testid="header-orders-btn"'),
    "Expected data-testid=\"header-orders-btn\" in header"
  );
  assert.ok(
    pageSource.includes("handleOpenOrderHistory"),
    "Expected handleOpenOrderHistory click handler in page.tsx"
  );
  assert.ok(
    pageSource.includes('aria-label="View order history"'),
    "Expected accessible aria-label on header orders button"
  );
});

test("2. Order History modal markup renders with proper dialog role and accessibility labels", () => {
  assert.ok(
    pageSource.includes('data-testid="order-history-modal"'),
    "Expected data-testid=\"order-history-modal\" in page.tsx"
  );
  assert.ok(
    pageSource.includes('role="dialog"'),
    "Expected role=\"dialog\" for accessible modal"
  );
  assert.ok(
    pageSource.includes('aria-labelledby="order-history-title"'),
    "Expected aria-labelledby=\"order-history-title\" attribute"
  );
  assert.ok(
    pageSource.includes('data-testid="order-history-close-btn"'),
    "Expected close button data-testid in order history modal"
  );
});

test("3. Successful order retrieval displays order summaries (ID, date, status, item count, total)", async () => {
  const originalFetch = global.fetch;
  let capturedUrl = "";
  let capturedHeaders: Record<string, string> = {};

  setStoredToken("test_customer_jwt_session");

  (global as unknown as { fetch: unknown }).fetch = async (
    input: RequestInfo | URL,
    init?: RequestInit
  ) => {
    capturedUrl = String(input);
    capturedHeaders = (init?.headers as Record<string, string>) || {};

    return new Response(JSON.stringify(sampleCustomerOrders), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const customerId = "cust-uuid-1";
    const res = await fetchCustomerOrders(customerId);

    assert.equal(capturedUrl, `${API_BASE_URL}/api/orders/${customerId}`);
    assert.equal(capturedHeaders["Authorization"], "Bearer test_customer_jwt_session");
    assert.equal(res.total, 2);
    assert.equal(res.items[0].status, "paid");
    assert.equal(res.items[1].status, "pending_payment");

    // Verify UI markup elements exist for rendering order items
    assert.ok(pageSource.includes('data-testid="order-card"'));
    assert.ok(pageSource.includes('data-testid="order-item-id"'));
    assert.ok(pageSource.includes('data-testid="order-item-status"'));
    assert.ok(pageSource.includes('data-testid="order-item-date"'));
    assert.ok(pageSource.includes('data-testid="order-item-total"'));
  } finally {
    global.fetch = originalFetch;
    clearAuth();
  }
});

test("4. Empty order state displays helpful guidance and catalog navigation", () => {
  assert.ok(
    pageSource.includes('data-testid="orders-empty-state"'),
    "Expected data-testid=\"orders-empty-state\" in page.tsx"
  );
  assert.ok(
    pageSource.includes("No Orders Placed Yet"),
    "Expected friendly empty-state message in page.tsx"
  );
  assert.ok(
    pageSource.includes("Browse Catalog"),
    "Expected catalog link or button in empty order state"
  );
});

test("5. Order status badges properly reflect authoritative status", () => {
  assert.ok(
    pageSource.includes("bg-emerald-950/80 text-emerald-300"),
    "Expected emerald styling for 'paid' order badge"
  );
  assert.ok(
    pageSource.includes("bg-amber-950/80 text-amber-300"),
    "Expected amber styling for 'pending_payment' order badge"
  );
  assert.ok(
    pageSource.includes("bg-rose-950/80 text-rose-300"),
    "Expected rose styling for 'cancelled' order badge"
  );
});

test("6. Order detail drill-down retrieves authoritative itemized receipt via fetchOrderDetail", async () => {
  const originalFetch = global.fetch;
  let capturedUrl = "";

  setStoredToken("test_customer_jwt_session");

  (global as unknown as { fetch: unknown }).fetch = async (
    input: RequestInfo | URL
  ) => {
    capturedUrl = String(input);
    return new Response(JSON.stringify(sampleCustomerOrders.items[0]), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const customerId = "cust-uuid-1";
    const orderId = "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d";
    const detail = await fetchOrderDetail(customerId, orderId);

    assert.equal(capturedUrl, `${API_BASE_URL}/api/orders/${customerId}/${orderId}`);
    assert.equal(detail.id, orderId);
    assert.equal(detail.items.length, 1);
    assert.equal(detail.items[0].product_name, "AuraPulse ANC Headphones");
    assert.equal(detail.items[0].sku, "AUD-AP-NC01");

    // Verify UI markup has required elements
    assert.ok(pageSource.includes('data-testid="order-detail-view"'));
    assert.ok(pageSource.includes('data-testid="order-detail-item"'));
    assert.ok(pageSource.includes('data-testid="order-detail-id"'));
    assert.ok(pageSource.includes('data-testid="order-detail-total"'));
  } finally {
    global.fetch = originalFetch;
    clearAuth();
  }
});

test("7. Order detail back button returns user to order list", () => {
  assert.ok(
    pageSource.includes('data-testid="order-detail-back-btn"'),
    "Expected data-testid=\"order-detail-back-btn\" in detail view"
  );
  assert.ok(
    pageSource.includes("Back to Orders"),
    "Expected 'Back to Orders' text in detail view"
  );
});

test("8. Loading and error states exist for both order list and order detail retrieval", () => {
  assert.ok(
    pageSource.includes('data-testid="orders-loading"'),
    "Expected data-testid=\"orders-loading\" in page.tsx"
  );
  assert.ok(
    pageSource.includes('data-testid="orders-error"'),
    "Expected data-testid=\"orders-error\" in page.tsx"
  );
  assert.ok(
    pageSource.includes("ordersLoading"),
    "Expected ordersLoading state in page.tsx"
  );
  assert.ok(
    pageSource.includes("detailOrderLoading"),
    "Expected detailOrderLoading state in page.tsx"
  );
});

test("9. Unauthenticated access guard renders sign-in guidance without querying backend orders", () => {
  assert.ok(
    pageSource.includes('data-testid="orders-unauth-view"'),
    "Expected data-testid=\"orders-unauth-view\" in page.tsx"
  );
  assert.ok(
    pageSource.includes('data-testid="order-history-signin-btn"'),
    "Expected data-testid=\"order-history-signin-btn\" in page.tsx"
  );
  assert.ok(
    pageSource.includes("Sign In to Access Your Order History"),
    "Expected sign-in prompt message in page.tsx"
  );
});

test("10. Checkout confirmation modal includes 'View Order History' action", () => {
  assert.ok(
    pageSource.includes('data-testid="order-confirmed-view-orders-btn"'),
    "Expected data-testid=\"order-confirmed-view-orders-btn\" in confirmedOrder modal"
  );
  assert.ok(
    pageSource.includes("View Order History"),
    "Expected 'View Order History' label in order confirmation modal"
  );
});

test("11. Customer ownership boundary enforced and zero machine keys leaked", () => {
  assert.ok(
    !pageSource.includes("COMMERCE_AGENT_KEY"),
    "page.tsx must not contain or reference COMMERCE_AGENT_KEY"
  );
  assert.ok(
    !pageSource.includes("X-Agent-Key"),
    "page.tsx must not contain or reference X-Agent-Key header"
  );
  assert.ok(
    pageSource.includes("fetchCustomerOrders(currentUser.id)"),
    "Orders must be fetched strictly with authenticated customer ID"
  );
  assert.ok(
    pageSource.includes("fetchOrderDetail(currentUser.id, orderId)"),
    "Order details must be fetched strictly with authenticated customer ID"
  );
});
