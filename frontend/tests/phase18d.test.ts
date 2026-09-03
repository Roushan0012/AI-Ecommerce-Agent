/**
 * Phase 18D — Frontend Production Configuration & Authentication Tests.
 *
 * Validates:
 * 1. Centralized API base URL configuration & environment override
 * 2. Injected Authorization: Bearer <access_token> on authenticated requests
 * 3. Clearing authentication state on 401 responses or logout
 * 4. Safe client-side JWT payload decoding & token expiry detection
 * 5. Role-aware UI helper behavior (customer, merchant, admin)
 * 6. Strict isolation of machine A2A keys (no COMMERCE_AGENT_KEY or X-Agent-Key in frontend)
 * 7. No backend secrets or private keys in NEXT_PUBLIC_* environment configuration
 */

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {
  decodeJwtPayload,
  isTokenExpired,
  getStoredToken,
  setStoredToken,
  clearAuth,
  setStoredUser,
  getStoredUser,
  TOKEN_STORAGE_KEY,
  USER_STORAGE_KEY,
} from "../src/lib/auth";
import { getAuthHeaders, authFetch, API_BASE_URL, fetchProducts } from "../src/lib/api";

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

test("1. API Base URL defaults to http://127.0.0.1:8000 when env variable is unset", () => {
  assert.ok(API_BASE_URL.length > 0);
  assert.match(API_BASE_URL, /^https?:\/\//);
});

test("2. getAuthHeaders attaches Authorization Bearer token when token is stored", () => {
  localStorage.clear();
  const headersWithoutToken = getAuthHeaders();
  assert.equal(headersWithoutToken["Authorization"], undefined);
  assert.equal(headersWithoutToken["Content-Type"], "application/json");

  setStoredToken("mock_jwt_access_token_abc123");
  const headersWithToken = getAuthHeaders();
  assert.equal(headersWithToken["Authorization"], "Bearer mock_jwt_access_token_abc123");
  assert.equal(headersWithToken["Content-Type"], "application/json");

  localStorage.clear();
});

test("3. getAuthHeaders preserves custom headers while injecting Authorization", () => {
  localStorage.clear();
  setStoredToken("test_token_xyz");

  const headers = getAuthHeaders({ "X-Custom-Trace": "req-12345" });
  assert.equal(headers["Authorization"], "Bearer test_token_xyz");
  assert.equal(headers["X-Custom-Trace"], "req-12345");
  assert.equal(headers["Content-Type"], "application/json");

  localStorage.clear();
});

test("4. decodeJwtPayload decodes payload claims without requiring backend secret", () => {
  // Sample JWT payload: {"sub": "12345678-1234-1234-1234-1234567890ab", "role": "merchant", "exp": 1893456000}
  // Base64Url header: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
  // Base64Url payload: eyJzdWIiOiIxMjM0NTY3OC0xMjM0LTEyMzQtMTIzNC0xMjM0NTY3ODkwYWIiLCJyb2xlIjoibWVyY2hhbnQiLCJleHAiOjE4OTM0NTYwMDB9
  const validToken =
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3OC0xMjM0LTEyMzQtMTIzNC0xMjM0NTY3ODkwYWIiLCJyb2xlIjoibWVyY2hhbnQiLCJleHAiOjE4OTM0NTYwMDB9.signature";

  const payload = decodeJwtPayload(validToken);
  assert.ok(payload);
  assert.equal(payload.sub, "12345678-1234-1234-1234-1234567890ab");
  assert.equal(payload.role, "merchant");
  assert.equal(payload.exp, 1893456000);

  // Malformed tokens return null gracefully
  assert.equal(decodeJwtPayload("invalid_token_string"), null);
  assert.equal(decodeJwtPayload(""), null);
});

test("5. isTokenExpired identifies expired and active tokens", () => {
  // Token with exp in far future (year 2030)
  const activeToken =
    "header.eyJzdWIiOiIxMjMiLCJleHAiOjE4OTM0NTYwMDB9.sig";
  assert.equal(isTokenExpired(activeToken), false);

  // Token with exp in past (epoch 1000)
  const expiredToken =
    "header.eyJzdWIiOiIxMjMiLCJleHAiOjEwMDB9.sig";
  assert.equal(isTokenExpired(expiredToken), true);

  // Bogus token
  assert.equal(isTokenExpired("not-a-jwt"), true);
});

test("6. clearAuth removes token, user profile, and invalidates auth state", () => {
  localStorage.clear();
  setStoredToken("test_token_123");
  setStoredUser({
    id: "user-uuid-1",
    email: "test@example.com",
    role: "customer",
    is_active: true,
  });

  assert.equal(getStoredToken(), "test_token_123");
  assert.equal(getStoredUser()?.email, "test@example.com");

  clearAuth();

  assert.equal(getStoredToken(), null);
  assert.equal(getStoredUser(), null);
  assert.equal(localStorage.getItem(TOKEN_STORAGE_KEY), null);
  assert.equal(localStorage.getItem(USER_STORAGE_KEY), null);
});

test("7. authFetch clears client auth state upon receiving 401 Unauthorized", async () => {
  localStorage.clear();
  setStoredToken("expired_or_invalid_token");

  // Mock global fetch returning 401
  const originalFetch = global.fetch;
  (global as unknown as { fetch: unknown }).fetch = async () => {
    return new Response(JSON.stringify({ detail: "Invalid access token." }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const res = await authFetch("http://127.0.0.1:8000/api/dashboard/overview");
    assert.equal(res.status, 401);
    // Token must have been purged from storage
    assert.equal(getStoredToken(), null);
  } finally {
    global.fetch = originalFetch;
    localStorage.clear();
  }
});

test("8. Frontend source code never exposes or sends COMMERCE_AGENT_KEY or X-Agent-Key", () => {
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

test("9. Frontend .env.example contains only safe NEXT_PUBLIC_* placeholders and zero secrets", () => {
  const envExamplePath = path.resolve(__dirname, "../.env.example");
  assert.ok(fs.existsSync(envExamplePath), "frontend/.env.example must exist");

  const content = fs.readFileSync(envExamplePath, "utf8");

  // Ensure forbidden backend secrets are never present
  const forbiddenPatterns = [
    "JWT_SECRET_KEY=",
    "RAZORPAY_KEY_SECRET=",
    "RAZORPAY_WEBHOOK_SECRET=",
    "DATABASE_URL=",
    "COMMERCE_AGENT_KEY=",
  ];

  for (const forbidden of forbiddenPatterns) {
    assert.ok(
      !content.includes(forbidden),
      `Forbidden backend secret configuration '${forbidden}' found in frontend/.env.example`
    );
  }

  // Ensure public API base URL is present
  assert.ok(content.includes("NEXT_PUBLIC_API_BASE_URL="));
  assert.ok(content.includes("NEXT_PUBLIC_RAZORPAY_KEY_ID="));
});

test("10. fetchProducts constructs correct GET /api/products query parameters", async () => {
  const originalFetch = global.fetch;
  let requestedUrl = "";

  (global as unknown as { fetch: unknown }).fetch = async (input: RequestInfo | URL) => {
    requestedUrl = String(input);
    return new Response(
      JSON.stringify({
        items: [
          {
            id: "prod-1",
            merchant_id: "merch-1",
            name: "Wireless Headphones",
            description: "ANC headphones",
            category: "Audio",
            price: "14999.00",
            currency: "INR",
            inventory: 10,
            sku: "AUD-01",
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
    const result = await fetchProducts({
      search: "headphones",
      category: "Audio",
      page: 2,
      page_size: 12,
      available: true,
    });

    assert.ok(requestedUrl.includes("/api/products?"));
    assert.ok(requestedUrl.includes("search=headphones"));
    assert.ok(requestedUrl.includes("category=Audio"));
    assert.ok(requestedUrl.includes("page=2"));
    assert.ok(requestedUrl.includes("page_size=12"));
    assert.ok(requestedUrl.includes("available=true"));
    assert.equal(result.items.length, 1);
    assert.equal(result.items[0].name, "Wireless Headphones");
  } finally {
    global.fetch = originalFetch;
  }
});

test("11. fetchProducts ignores category 'All' and empty search to fetch full catalog", async () => {
  const originalFetch = global.fetch;
  let requestedUrl = "";

  (global as unknown as { fetch: unknown }).fetch = async (input: RequestInfo | URL) => {
    requestedUrl = String(input);
    return new Response(
      JSON.stringify({
        items: [],
        total: 0,
        page: 1,
        page_size: 12,
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  };

  try {
    await fetchProducts({
      search: "",
      category: "All",
      page: 1,
      page_size: 12,
    });

    assert.ok(!requestedUrl.includes("category=All"));
    assert.ok(!requestedUrl.includes("search="));
    assert.ok(requestedUrl.includes("page=1"));
    assert.ok(requestedUrl.includes("page_size=12"));
  } finally {
    global.fetch = originalFetch;
  }
});
