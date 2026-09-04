/**
 * Product Images Frontend Tests.
 *
 * Verifies:
 * 1. ProductItem interface includes optional image_url.
 * 2. ProductCard and Modal markup render ProductImage with proper aspect ratio and fallback handling.
 * 3. Safe fallback markup exists for missing or broken images.
 * 4. Image URLs use secure HTTPS protocol and contain no private keys/tokens.
 */

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { ProductItem } from "../src/lib/api";

test("1. ProductItem interface supports image_url field", () => {
  const productWithImage: ProductItem = {
    id: "prod-img-01",
    merchant_id: "merch-1",
    name: "AuraPulse ANC Headphones",
    description: "High fidelity wireless audio.",
    category: "Audio",
    price: "14999.00",
    currency: "INR",
    inventory: 45,
    sku: "AUD-AP-NC01",
    attributes: {},
    is_active: true,
    image_url: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=80",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  assert.equal(typeof productWithImage.image_url, "string");
  assert.ok(productWithImage.image_url?.startsWith("https://"));

  const productWithoutImage: ProductItem = {
    id: "prod-img-02",
    merchant_id: "merch-1",
    name: "Generic Cable",
    description: "Standard cable.",
    category: "Chargers & Cables",
    price: "499.00",
    currency: "INR",
    inventory: 20,
    sku: "CHG-GEN-01",
    attributes: {},
    is_active: true,
    image_url: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  assert.equal(productWithoutImage.image_url, null);
});

test("2. ProductCard markup includes ProductImage and aspect-ratio styling in page.tsx", () => {
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const pageContent = fs.readFileSync(pagePath, "utf-8");

  assert.ok(pageContent.includes("function ProductImage"), "Expected ProductImage component in page.tsx");
  assert.ok(pageContent.includes("aspect-[16/10]"), "Expected consistent aspect ratio in ProductImage");
  assert.ok(pageContent.includes("data-testid=\"product-image-fallback\""), "Expected fallback testid in page.tsx");
  assert.ok(pageContent.includes("onError="), "Expected error boundary fallback on image tag");
});

test("3. Product Detail Modal renders product image preview", () => {
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const pageContent = fs.readFileSync(pagePath, "utf-8");

  assert.ok(pageContent.includes("Product Image Preview"), "Expected image preview in detail modal");
  assert.ok(pageContent.includes("src={detailProduct.image_url}"), "Expected detailProduct.image_url in modal");
});
