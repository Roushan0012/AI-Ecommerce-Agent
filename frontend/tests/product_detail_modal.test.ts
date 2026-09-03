/**
 * Product Details Modal Frontend Tests.
 *
 * Verifies:
 * 1. Product card markup includes clearly visible "View Details" button distinct from "Add to Cart".
 * 2. Opening product details uses the product UUID and calls GET /api/products/{product_id}.
 * 3. Authoritative product details (name, SKU, category, description, price, stock, attributes) are parsed from the response.
 * 4. Backend error handling for non-existent product IDs.
 * 5. Add to Cart within the modal reuses the authenticated cart flow (POST /api/cart/{customerId}/items).
 * 6. Frontend source code never leaks or references COMMERCE_AGENT_KEY or X-Agent-Key.
 */

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {
  fetchProductById,
  addToCart,
  API_BASE_URL,
  ProductItem,
  CartResponse,
} from "../src/lib/api";
import { setStoredToken, clearAuth } from "../src/lib/auth";

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

test("1. Product card renders a distinct View Details control alongside Add to Cart", () => {
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const pageCode = fs.readFileSync(pagePath, "utf8");

  // Verify dedicated View Details button exists
  assert.ok(
    pageCode.includes('data-testid="view-details-btn"'),
    "Expected data-testid=\"view-details-btn\" in ProductCard"
  );
  assert.ok(
    pageCode.includes("View Details"),
    "Expected visible 'View Details' button text in ProductCard"
  );

  // Verify dedicated Add to Cart button exists
  assert.ok(
    pageCode.includes('data-testid="add-to-cart-btn"'),
    "Expected data-testid=\"add-to-cart-btn\" in ProductCard"
  );
  assert.ok(
    pageCode.includes("Add to Cart"),
    "Expected visible 'Add to Cart' button text in ProductCard"
  );

  // Verify onOpenDetails is wired in both AI and catalog cards
  assert.ok(
    pageCode.includes("onOpenDetails={handleOpenProductDetail}"),
    "Expected onOpenDetails to be wired to handleOpenProductDetail"
  );
});

test("2. Opening product details uses the product UUID and calls GET /api/products/{product_id}", async () => {
  const originalFetch = global.fetch;
  let capturedUrl = "";
  let capturedMethod = "";

  const mockProduct: ProductItem = {
    id: "465206d3-bd4d-4f9f-b705-010670ab4006",
    merchant_id: "merch-1",
    name: "AuraPulse Wireless Noise-Cancelling Headphones",
    description: "Adaptive hybrid ANC, 40mm hi-res drivers, 45-hour battery life.",
    category: "Audio",
    price: "14999.00",
    currency: "INR",
    inventory: 45,
    sku: "AUD-AP-NC01",
    attributes: {
      battery_life: "45 hours",
      connectivity: "Bluetooth 5.3",
      weight: "250g",
    },
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  (global as unknown as { fetch: unknown }).fetch = async (
    input: RequestInfo | URL,
    init?: RequestInit
  ) => {
    capturedUrl = String(input);
    capturedMethod = init?.method || "GET";

    return new Response(JSON.stringify(mockProduct), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const productId = "465206d3-bd4d-4f9f-b705-010670ab4006";
    const product = await fetchProductById(productId);

    // Verify correct endpoint and UUID
    assert.equal(capturedUrl, `${API_BASE_URL}/api/products/${productId}`);
    assert.equal(capturedMethod, "GET");

    // Verify all authoritative attributes for modal rendering
    assert.equal(product.id, productId);
    assert.equal(product.name, "AuraPulse Wireless Noise-Cancelling Headphones");
    assert.equal(product.sku, "AUD-AP-NC01");
    assert.equal(product.category, "Audio");
    assert.equal(product.price, "14999.00");
    assert.equal(product.inventory, 45);
    assert.equal(product.is_active, true);
    assert.equal(product.attributes.battery_life, "45 hours");
    assert.equal(product.attributes.connectivity, "Bluetooth 5.3");
  } finally {
    global.fetch = originalFetch;
  }
});

test("3. Backend error on product details retrieval surfaces readable message", async () => {
  const originalFetch = global.fetch;

  (global as unknown as { fetch: unknown }).fetch = async () => {
    return new Response(
      JSON.stringify({ detail: "Product not found or inactive." }),
      {
        status: 404,
        headers: { "Content-Type": "application/json" },
      }
    );
  };

  try {
    await assert.rejects(
      async () => {
        await fetchProductById("non-existent-id");
      },
      {
        name: "Error",
        message: "Product not found or inactive.",
      }
    );
  } finally {
    global.fetch = originalFetch;
  }
});

test("4. Add to Cart in modal reuses the authenticated cart flow", async () => {
  const originalFetch = global.fetch;
  let capturedUrl = "";
  let capturedMethod = "";
  let capturedHeaders: Record<string, string> = {};
  let capturedBody: any = null;

  setStoredToken("test_customer_jwt_token_modal");

  const mockCart: CartResponse = {
    id: "cart-modal-1",
    customer_id: "cust-modal-1",
    status: "active",
    currency: "INR",
    items: [
      {
        id: "item-modal-1",
        cart_id: "cart-modal-1",
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
    const customerId = "cust-modal-1";
    const productId = "465206d3-bd4d-4f9f-b705-010670ab4006";

    const updatedCart = await addToCart(customerId, productId, 1);

    // Reuses the identical cart mutation endpoint
    assert.equal(capturedUrl, `${API_BASE_URL}/api/cart/${customerId}/items`);
    assert.equal(capturedMethod, "POST");
    assert.equal(capturedHeaders["Authorization"], "Bearer test_customer_jwt_token_modal");
    assert.equal(capturedBody.product_id, productId);
    assert.equal(capturedBody.quantity, 1);

    assert.equal(updatedCart.item_count, 1);
    assert.equal(updatedCart.total, "14999.00");
  } finally {
    clearAuth();
    global.fetch = originalFetch;
  }
});

test("5. Frontend source code never leaks or references COMMERCE_AGENT_KEY or X-Agent-Key", () => {
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
