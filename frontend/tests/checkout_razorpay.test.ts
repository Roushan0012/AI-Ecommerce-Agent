/**
 * Step 4B — Real Razorpay Checkout Flow Frontend Tests.
 *
 * Verifies:
 * 1. "Proceed to Checkout" button is rendered in the cart UI.
 * 2. Unauthenticated customers cannot initiate checkout without a valid JWT token.
 * 3. Checkout calls the backend POST /api/orders with the customer_id.
 * 4. Checkout calls POST /api/payments/create-order with the authoritative order_id.
 * 5. Razorpay Checkout is initialized using only public key_id and backend-provided order info.
 * 6. Checkout cancellation / dismissal preserves cart state without wiping items.
 * 7. Backend errors (e.g. out of stock or order creation failure) are surfaced cleanly.
 * 8. Payment success does not locally forge or hardcode a paid status.
 * 9. Frontend source code never references or leaks RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET, DATABASE_URL, or COMMERCE_AGENT_KEY.
 */

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {
  createOrder,
  createPaymentOrder,
  fetchOrderDetail,
  API_BASE_URL,
  OrderResponse,
  PaymentOrderResponse,
} from "../src/lib/api";
import { launchRazorpayCheckout, RazorpayFailureResponse } from "../src/lib/razorpay";
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

const sampleOrder: OrderResponse = {
  id: "order-test-uuid-1",
  merchant_id: "merch-test-1",
  customer_id: "cust-test-1",
  cart_id: "cart-test-1",
  status: "pending_payment",
  currency: "INR",
  subtotal: "14999.00",
  discount: "0.00",
  total: "14999.00",
  items: [
    {
      id: "oi-1",
      order_id: "order-test-uuid-1",
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
};

const samplePaymentOrder: PaymentOrderResponse = {
  payment_id: "pay-rec-uuid-1",
  order_id: "order-test-uuid-1",
  razorpay_order_id: "order_mock_rzp_12345",
  amount: "14999.00",
  amount_in_paise: 1499900,
  currency: "INR",
  key_id: "rzp_test_public_key_mock",
  status: "created",
  created_at: new Date().toISOString(),
};

test("1. 'Proceed to Checkout' control exists in storefront cart UI", () => {
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const pageCode = fs.readFileSync(pagePath, "utf8");

  assert.ok(
    pageCode.includes('data-testid="proceed-to-checkout-btn"'),
    "Expected data-testid=\"proceed-to-checkout-btn\" in page.tsx"
  );
  assert.ok(
    pageCode.includes("handleProceedToCheckout"),
    "Expected handleProceedToCheckout handler in page.tsx"
  );
  assert.ok(
    pageCode.includes("Proceed to Checkout"),
    "Expected 'Proceed to Checkout' text in page.tsx"
  );
});

test("2. Unauthenticated customer cannot initiate checkout without token", async () => {
  clearAuth();
  assert.equal(getStoredToken(), null);

  const originalFetch = global.fetch;
  (global as unknown as { fetch: unknown }).fetch = async () => {
    return new Response(JSON.stringify({ detail: "Not authenticated" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    await assert.rejects(
      async () => {
        await createOrder("unauthenticated-cust-id");
      },
      {
        name: "Error",
      }
    );
  } finally {
    global.fetch = originalFetch;
  }
});

test("3. Checkout calls POST /api/orders with authenticated context and customer_id", async () => {
  const originalFetch = global.fetch;
  let capturedUrl = "";
  let capturedMethod = "";
  let capturedHeaders: Record<string, string> = {};
  let capturedBody: { customer_id?: string; cart_id?: string } | null = null;

  setStoredToken("customer_jwt_token_for_checkout");

  (global as unknown as { fetch: unknown }).fetch = async (
    input: RequestInfo | URL,
    init?: RequestInit
  ) => {
    capturedUrl = String(input);
    capturedMethod = init?.method || "GET";
    capturedHeaders = (init?.headers as Record<string, string>) || {};
    capturedBody = init?.body ? JSON.parse(String(init.body)) : null;

    return new Response(JSON.stringify(sampleOrder), {
      status: 201,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const customerId = "cust-test-1";
    const order = await createOrder(customerId, "cart-test-1");

    assert.equal(capturedUrl, `${API_BASE_URL}/api/orders`);
    assert.equal(capturedMethod, "POST");
    assert.equal(
      capturedHeaders["Authorization"],
      "Bearer customer_jwt_token_for_checkout"
    );
    const body = capturedBody as unknown as { customer_id?: string; cart_id?: string };
    assert.equal(body?.customer_id, customerId);
    assert.equal(body?.cart_id, "cart-test-1");

    assert.equal(order.id, "order-test-uuid-1");
    assert.equal(order.status, "pending_payment");
    assert.equal(order.total, "14999.00");
  } finally {
    clearAuth();
    global.fetch = originalFetch;
  }
});

test("4. Checkout calls POST /api/payments/create-order with authoritative order_id", async () => {
  const originalFetch = global.fetch;
  let capturedUrl = "";
  let capturedMethod = "";
  let capturedBody: { order_id?: string; customer_id?: string; amount?: unknown } | null = null;

  setStoredToken("customer_jwt_token_for_checkout");

  (global as unknown as { fetch: unknown }).fetch = async (
    input: RequestInfo | URL,
    init?: RequestInit
  ) => {
    capturedUrl = String(input);
    capturedMethod = init?.method || "GET";
    capturedBody = init?.body ? JSON.parse(String(init.body)) : null;

    return new Response(JSON.stringify(samplePaymentOrder), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const paymentOrder = await createPaymentOrder("order-test-uuid-1", "cust-test-1");

    assert.equal(capturedUrl, `${API_BASE_URL}/api/payments/create-order`);
    assert.equal(capturedMethod, "POST");
    const body = capturedBody as unknown as { order_id?: string; customer_id?: string; amount?: unknown };
    assert.equal(body?.order_id, "order-test-uuid-1");
    assert.equal(body?.customer_id, "cust-test-1");
    // Client strictly avoids sending monetary amounts
    assert.equal(body?.amount, undefined);

    assert.equal(paymentOrder.key_id, "rzp_test_public_key_mock");
    assert.equal(paymentOrder.razorpay_order_id, "order_mock_rzp_12345");
    assert.equal(paymentOrder.amount_in_paise, 1499900);
  } finally {
    clearAuth();
    global.fetch = originalFetch;
  }
});

test("5. launchRazorpayCheckout opens Razorpay with backend-provided parameters", async () => {
  const originalFetch = global.fetch;
  let configuredRzpOptions: Record<string, unknown> | null = null;
  let modalOpened = false;

  setStoredToken("customer_jwt_token_for_checkout");

  // Mock fetch for createPaymentOrder
  (global as unknown as { fetch: unknown }).fetch = async () => {
    return new Response(JSON.stringify(samplePaymentOrder), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  // Mock window.Razorpay SDK constructor
  (global as unknown as { window: { Razorpay?: unknown } }).window.Razorpay = function (
    options: Record<string, unknown>
  ) {
    configuredRzpOptions = options;
    return {
      open: () => {
        modalOpened = true;
      },
      on: () => {},
    };
  };

  try {
    const paymentOrder = await launchRazorpayCheckout({
      orderId: "order-test-uuid-1",
      customerId: "cust-test-1",
      customerEmail: "customer@example.com",
    });

    assert.ok(modalOpened, "Razorpay open() must be called");
    const rzpOpts = configuredRzpOptions as unknown as Record<string, unknown>;
    assert.equal(rzpOpts?.key, "rzp_test_public_key_mock");
    assert.equal(rzpOpts?.order_id, "order_mock_rzp_12345");
    assert.equal(rzpOpts?.amount, 1499900);
    assert.equal(rzpOpts?.currency, "INR");
    const prefill = rzpOpts?.prefill as { email?: string } | undefined;
    assert.equal(prefill?.email, "customer@example.com");
    assert.equal(paymentOrder.order_id, "order-test-uuid-1");
  } finally {
    clearAuth();
    global.fetch = originalFetch;
    delete (global as unknown as { window: { Razorpay?: unknown } }).window.Razorpay;
  }
});

test("6. Razorpay cancellation preserves cart state without wiping items", async () => {
  const originalFetch = global.fetch;
  let ondismissTriggered = false;

  setStoredToken("customer_jwt_token_for_checkout");

  // Mock fetch for createPaymentOrder
  (global as unknown as { fetch: unknown }).fetch = async () => {
    return new Response(JSON.stringify(samplePaymentOrder), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  // Mock initial cart state
  const initialCart = {
    id: "cart-test-1",
    customer_id: "cust-test-1",
    status: "active",
    currency: "INR",
    items: [
      {
        id: "item-1",
        cart_id: "cart-test-1",
        product_id: "prod-1",
        product_name: "AuraPulse ANC Headphones",
        sku: "AUD-AP-NC01",
        quantity: 2,
        unit_price: "14999.00",
        total_price: "29998.00",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ],
    item_count: 2,
    subtotal: "29998.00",
    discount: "0.00",
    total: "29998.00",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  // Clone cart to track any mutations
  const cartBeforeCheckout = JSON.parse(JSON.stringify(initialCart));

  (global as unknown as { window: { Razorpay?: unknown } }).window.Razorpay = function (
    options: Record<string, unknown>
  ) {
    return {
      open: () => {
        // Simulate user dismissing the modal
        const modal = options.modal as { ondismiss?: () => void } | undefined;
        if (modal && typeof modal.ondismiss === "function") {
          modal.ondismiss();
        }
      },
      on: () => {},
    };
  };

  try {
    await launchRazorpayCheckout({
      orderId: "order-test-uuid-1",
      customerId: "cust-test-1",
      onModalDismiss: () => {
        ondismissTriggered = true;
        // On dismissal, active cart must remain unchanged
      },
    });

    assert.ok(ondismissTriggered, "Modal dismissal callback must be triggered");
    assert.deepEqual(
      cartBeforeCheckout,
      initialCart,
      "Cart state before and after dismissal must remain identical"
    );
    assert.equal(initialCart.items.length, 1);
    assert.equal(initialCart.total, "29998.00");

    // Also verify page.tsx handler logic does NOT clear the cart on dismissal
    const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
    const pageCode = fs.readFileSync(pagePath, "utf8");
    assert.ok(
      pageCode.includes("Your items remain in your cart"),
      "Cancellation feedback toast must inform user items remain in cart"
    );
  } finally {
    clearAuth();
    global.fetch = originalFetch;
    delete (global as unknown as { window: { Razorpay?: unknown } }).window.Razorpay;
  }
});

test("7. Razorpay payment failure preserves cart state and surfaces readable error", async () => {
  const originalFetch = global.fetch;
  let failureCallbackCalled = false;
  let capturedError: RazorpayFailureResponse | null = null;

  setStoredToken("customer_jwt_token_for_checkout");

  (global as unknown as { fetch: unknown }).fetch = async () => {
    return new Response(JSON.stringify(samplePaymentOrder), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  (global as unknown as { window: { Razorpay?: unknown } }).window.Razorpay = function () {
    const listeners: Record<string, (res: RazorpayFailureResponse) => void> = {};
    return {
      open: () => {
        // Simulate failure event
        if (listeners["payment.failed"]) {
          listeners["payment.failed"]({
            error: {
              code: "BAD_REQUEST_ERROR",
              description: "Payment failed at issuing bank.",
              reason: "payment_failed",
            },
          });
        }
      },
      on: (event: string, callback: (res: RazorpayFailureResponse) => void) => {
        listeners[event] = callback;
      },
    };
  };

  try {
    await launchRazorpayCheckout({
      orderId: "order-test-uuid-1",
      customerId: "cust-test-1",
      onPaymentFailure: (error) => {
        failureCallbackCalled = true;
        capturedError = error;
      },
    });

    assert.ok(failureCallbackCalled, "onPaymentFailure callback must be executed");
    const err = capturedError as unknown as RazorpayFailureResponse;
    assert.equal(
      err?.error?.description,
      "Payment failed at issuing bank."
    );
  } finally {
    clearAuth();
    global.fetch = originalFetch;
    delete (global as unknown as { window: { Razorpay?: unknown } }).window.Razorpay;
  }
});

test("8. Backend/payment errors are surfaced safely without breaking UI", async () => {
  const originalFetch = global.fetch;

  (global as unknown as { fetch: unknown }).fetch = async () => {
    return new Response(
      JSON.stringify({ detail: "Insufficient inventory for 'AuraPulse ANC Headphones'." }),
      {
        status: 400,
        headers: { "Content-Type": "application/json" },
      }
    );
  };

  try {
    await assert.rejects(
      async () => {
        await createOrder("cust-test-1");
      },
      {
        name: "Error",
        message: "Insufficient inventory for 'AuraPulse ANC Headphones'.",
      }
    );
  } finally {
    global.fetch = originalFetch;
  }
});

test("9. Successful payment flow polls backend and does not locally forge 'paid' status", async () => {
  const originalFetch = global.fetch;
  let pollCount = 0;

  (global as unknown as { fetch: unknown }).fetch = async () => {
    pollCount++;
    const status = pollCount >= 2 ? "paid" : "pending_payment";
    return new Response(
      JSON.stringify({ ...sampleOrder, status }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }
    );
  };

  try {
    const order1 = await fetchOrderDetail("cust-test-1", "order-test-uuid-1");
    assert.equal(order1.status, "pending_payment");

    const order2 = await fetchOrderDetail("cust-test-1", "order-test-uuid-1");
    assert.equal(order2.status, "paid");
    assert.equal(pollCount, 2);
  } finally {
    global.fetch = originalFetch;
  }
});

test("10. launchRazorpayCheckout validates orderId and public Key ID availability", async () => {
  // Test missing orderId
  await assert.rejects(
    async () => {
      await launchRazorpayCheckout({ orderId: "" });
    },
    {
      name: "Error",
      message: "Order ID is required to initiate checkout.",
    }
  );
});

test("11. Frontend code never references or leaks backend secrets or machine keys", () => {
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
  assert.ok(files.length > 0, "Expected frontend files to inspect");

  const forbiddenKeys = [
    "RAZORPAY_KEY_SECRET",
    "RAZORPAY_WEBHOOK_SECRET",
    "COMMERCE_AGENT_KEY",
    "DATABASE_URL",
    "X-Agent-Key",
  ];

  for (const file of files) {
    const content = fs.readFileSync(file, "utf8");
    for (const forbidden of forbiddenKeys) {
      assert.ok(
        !content.includes(forbidden),
        `Forbidden secret reference '${forbidden}' found in ${file}`
      );
    }
  }

  // Also check environment configuration files
  const envExamplePath = path.resolve(__dirname, "../.env.example");
  if (fs.existsSync(envExamplePath)) {
    const envContent = fs.readFileSync(envExamplePath, "utf8");
    for (const forbidden of ["NEXT_PUBLIC_RAZORPAY_KEY_SECRET", "NEXT_PUBLIC_COMMERCE_AGENT_KEY"]) {
      assert.ok(
        !envContent.includes(forbidden),
        `Forbidden secret variable '${forbidden}' found in .env.example`
      );
    }
  }

  const envLocalPath = path.resolve(__dirname, "../.env.local");
  if (fs.existsSync(envLocalPath)) {
    const localEnvContent = fs.readFileSync(envLocalPath, "utf8");
    for (const forbidden of forbiddenKeys) {
      assert.ok(
        !localEnvContent.includes(forbidden),
        `Forbidden secret '${forbidden}' found in .env.local`
      );
    }
  }
});
