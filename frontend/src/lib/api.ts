/**
 * Production API Client & Request Handling (Phase 18D).
 *
 * Centralizes all frontend HTTP requests to the backend service.
 * Automatically injects the JWT access token as Authorization: Bearer <token>
 * on authenticated requests and clears client auth state on 401 Unauthorized.
 *
 * SECURITY GUARANTEES:
 * - API base URL is driven by NEXT_PUBLIC_API_BASE_URL (defaults to http://127.0.0.1:8000).
 * - Never includes or transmits machine agent authentication headers.
 * - Never exposes signing keys or backend secrets to the browser.
 */

import {
  AuthUser,
  clearAuth,
  getStoredToken,
  isTokenExpired,
  setStoredToken,
  setStoredUser,
} from "./auth";

export interface HealthResponse {
  status: string;
  service: string;
}

export interface ProductItem {
  id: string;
  merchant_id: string;
  name: string;
  description: string | null;
  category: string | null;
  price: string | number;
  currency: string;
  inventory: number;
  sku: string;
  attributes: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductListResponse {
  items: ProductItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface FetchProductsParams {
  search?: string;
  category?: string;
  min_price?: number;
  max_price?: number;
  available?: boolean;
  page?: number;
  page_size?: number;
}

export interface ShoppingIntent {
  intent: "product_search" | "general" | "inquiry";
  search_query?: string | null;
  category?: string | null;
  min_price?: number | string | null;
  max_price?: number | string | null;
  currency: string;
  availability_required: boolean;
}

export interface AgentSearchRequest {
  message: string;
  page?: number;
  page_size?: number;
}

export interface AgentSearchResponse {
  message: string;
  intent: ShoppingIntent;
  items: ProductItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface RecommendedProductItem {
  product: ProductItem;
  score: number;
  reason: string;
}

export interface AgentRecommendRequest {
  message: string;
  page?: number;
  page_size?: number;
}

export interface AgentRecommendResponse {
  message: string;
  intent: ShoppingIntent;
  items: RecommendedProductItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface GrowthRecommendationItem {
  type: "upsell" | "cross_sell";
  product: ProductItem;
  primary_product_id: string;
  primary_product_name: string;
  score: number;
  reason: string;
}

export interface AgentGrowthRequest {
  message: string;
  page?: number;
  page_size?: number;
}

export interface AgentGrowthResponse {
  message: string;
  intent: ShoppingIntent;
  primary_products: ProductItem[];
  upsell: GrowthRecommendationItem[];
  cross_sell: GrowthRecommendationItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface PaymentOrderResponse {
  payment_id: string;
  order_id: string;
  razorpay_order_id: string;
  amount: string | number;
  amount_in_paise: number;
  currency: string;
  key_id: string;
  status: string;
  created_at: string;
}

export interface OverviewMetricsResponse {
  total_revenue: string | number;
  paid_orders_count: number;
  total_orders_count: number;
  average_order_value: string | number;
  conversion_rate: number;
  ai_assisted_orders_count: number;
  ai_assisted_revenue: string | number;
  ai_assisted_percentage: number;
  recommendations_generated: number;
  recommendations_accepted: number;
  recommendation_acceptance_rate: number;
  upsell_count: number;
  upsell_revenue: string | number;
  cross_sell_count: number;
  cross_sell_revenue: string | number;
  currency: string;
}

export interface DashboardOrderItem {
  id: string;
  customer_id: string;
  total: string | number;
  currency: string;
  status: string;
  payment_status?: string | null;
  items_count: number;
  is_ai_assisted: boolean;
  created_at: string;
}

export interface DashboardOrdersResponse {
  items: DashboardOrderItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface DashboardActivityItem {
  id: string;
  event_type: string;
  action?: string | null;
  status: string;
  customer_id?: string | null;
  cart_id?: string | null;
  order_id?: string | null;
  error_message?: string | null;
  created_at: string;
}

export interface DashboardActivityResponse {
  items: DashboardActivityItem[];
  total: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export const API_BASE_URL: string =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

/**
 * Constructs standard headers, optionally attaching Authorization: Bearer <token>.
 */
export function getAuthHeaders(
  extraHeaders: Record<string, string> = {}
): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...extraHeaders,
  };

  const token = getStoredToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
}

/**
 * Standard fetch wrapper that handles Authorization headers and 401 state invalidation.
 */
export async function authFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const customHeaders = (options.headers as Record<string, string>) || {};
  const mergedHeaders = getAuthHeaders(customHeaders);

  const response = await fetch(url, {
    ...options,
    headers: mergedHeaders,
  });

  if (response.status === 401) {
    // Invalidate client authentication state on rejected or expired credentials
    clearAuth();
  }

  return response;
}

// -----------------------------------------------------------------------------
// Public Endpoints
// -----------------------------------------------------------------------------

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Health check request failed with status ${response.status}`);
  }

  const data: HealthResponse = await response.json();
  return data;
}

export async function fetchProducts(
  params: FetchProductsParams = {}
): Promise<ProductListResponse> {
  const searchParams = new URLSearchParams();

  if (params.search && params.search.trim()) {
    searchParams.set("search", params.search.trim());
  }
  if (params.category && params.category !== "All") {
    searchParams.set("category", params.category);
  }
  if (params.min_price !== undefined) {
    searchParams.set("min_price", params.min_price.toString());
  }
  if (params.max_price !== undefined) {
    searchParams.set("max_price", params.max_price.toString());
  }
  if (params.available !== undefined) {
    searchParams.set("available", params.available.toString());
  }
  if (params.page !== undefined) {
    searchParams.set("page", params.page.toString());
  }
  if (params.page_size !== undefined) {
    searchParams.set("page_size", params.page_size.toString());
  }

  const queryString = searchParams.toString();
  const url = `${API_BASE_URL}/api/products${queryString ? `?${queryString}` : ""}`;

  const response = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message =
      typeof errorData.detail === "string"
        ? errorData.detail
        : `Failed to fetch products (status ${response.status})`;
    throw new Error(message);
  }

  const data: ProductListResponse = await response.json();
  return data;
}

// -----------------------------------------------------------------------------
// AI Agent Endpoints
// -----------------------------------------------------------------------------

export async function searchWithAgent(
  request: AgentSearchRequest
): Promise<AgentSearchResponse> {
  const trimmed = request.message ? request.message.trim() : "";
  if (!trimmed) {
    throw new Error("Message cannot be empty.");
  }

  const response = await authFetch(`${API_BASE_URL}/api/agent/search`, {
    method: "POST",
    body: JSON.stringify({
      message: trimmed,
      page: request.page || 1,
      page_size: request.page_size || 10,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message =
      typeof errorData.detail === "string"
        ? errorData.detail
        : `AI search failed with status ${response.status}`;
    throw new Error(message);
  }

  return response.json();
}

export async function getAgentRecommendations(
  request: AgentRecommendRequest
): Promise<AgentRecommendResponse> {
  const trimmed = request.message ? request.message.trim() : "";
  if (!trimmed) {
    throw new Error("Message cannot be empty.");
  }

  const response = await authFetch(`${API_BASE_URL}/api/agent/recommend`, {
    method: "POST",
    body: JSON.stringify({
      message: trimmed,
      page: request.page || 1,
      page_size: request.page_size || 10,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message =
      typeof errorData.detail === "string"
        ? errorData.detail
        : `AI recommendations failed with status ${response.status}`;
    throw new Error(message);
  }

  return response.json();
}

export async function getAgentGrowth(
  request: AgentGrowthRequest
): Promise<AgentGrowthResponse> {
  const trimmed = request.message ? request.message.trim() : "";
  if (!trimmed) {
    throw new Error("Message cannot be empty.");
  }

  const response = await authFetch(`${API_BASE_URL}/api/agent/growth`, {
    method: "POST",
    body: JSON.stringify({
      message: trimmed,
      page: request.page || 1,
      page_size: request.page_size || 10,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message =
      typeof errorData.detail === "string"
        ? errorData.detail
        : `AI growth suggestions failed with status ${response.status}`;
    throw new Error(message);
  }

  return response.json();
}

// -----------------------------------------------------------------------------
// Authentication Endpoints
// -----------------------------------------------------------------------------

export async function loginUser(
  email: string,
  password: string
): Promise<{ token: string; user: AuthUser }> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message =
      typeof errorData.detail === "string"
        ? errorData.detail
        : `Login failed with status ${response.status}`;
    throw new Error(message);
  }

  const tokenData: TokenResponse = await response.json();
  setStoredToken(tokenData.access_token);

  // Fetch authoritative user profile with the newly issued token
  const meResponse = await authFetch(`${API_BASE_URL}/api/auth/me`);
  if (!meResponse.ok) {
    clearAuth();
    throw new Error("Failed to load user profile after login");
  }

  const user: AuthUser = await meResponse.json();
  setStoredUser(user);

  return { token: tokenData.access_token, user };
}

export async function registerUser(
  email: string,
  password: string
): Promise<AuthUser> {
  const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message =
      typeof errorData.detail === "string"
        ? errorData.detail
        : Array.isArray(errorData.detail)
        ? errorData.detail.map((e: { msg?: string }) => e.msg).join(", ")
        : `Registration failed with status ${response.status}`;
    throw new Error(message);
  }

  const user: AuthUser = await response.json();
  return user;
}

export async function fetchCurrentUser(): Promise<AuthUser | null> {
  const token = getStoredToken();
  if (!token || isTokenExpired(token)) {
    clearAuth();
    return null;
  }

  try {
    const response = await authFetch(`${API_BASE_URL}/api/auth/me`);
    if (!response.ok) {
      clearAuth();
      return null;
    }
    const user: AuthUser = await response.json();
    setStoredUser(user);
    return user;
  } catch {
    clearAuth();
    return null;
  }
}

export function logoutUser(): void {
  clearAuth();
}

// -----------------------------------------------------------------------------
// Protected Merchant Dashboard Endpoints
// -----------------------------------------------------------------------------

export async function fetchDashboardOverview(): Promise<OverviewMetricsResponse> {
  const response = await authFetch(`${API_BASE_URL}/api/dashboard/overview`, {
    method: "GET",
    cache: "no-store",
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Authentication required. Please log in to view merchant data.");
    }
    if (response.status === 403) {
      throw new Error("Access forbidden. Merchant or admin role is required.");
    }
    throw new Error(`Failed to load dashboard overview (status ${response.status})`);
  }

  return response.json();
}

export async function fetchDashboardOrders(
  page: number = 1,
  pageSize: number = 10
): Promise<DashboardOrdersResponse> {
  const response = await authFetch(
    `${API_BASE_URL}/api/dashboard/orders?page=${page}&page_size=${pageSize}`,
    {
      method: "GET",
      cache: "no-store",
    }
  );

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Authentication required. Please log in to view merchant data.");
    }
    if (response.status === 403) {
      throw new Error("Access forbidden. Merchant or admin role is required.");
    }
    throw new Error(`Failed to load dashboard orders (status ${response.status})`);
  }

  return response.json();
}

export async function fetchDashboardActivity(
  limit: number = 10
): Promise<DashboardActivityResponse> {
  const response = await authFetch(
    `${API_BASE_URL}/api/dashboard/activity?limit=${limit}`,
    {
      method: "GET",
      cache: "no-store",
    }
  );

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Authentication required. Please log in to view merchant data.");
    }
    if (response.status === 403) {
      throw new Error("Access forbidden. Merchant or admin role is required.");
    }
    throw new Error(`Failed to load dashboard activity (status ${response.status})`);
  }

  return response.json();
}

// -----------------------------------------------------------------------------
// Payment Endpoints
// -----------------------------------------------------------------------------

export async function createPaymentOrder(
  orderId: string,
  customerId?: string
): Promise<PaymentOrderResponse> {
  const response = await authFetch(`${API_BASE_URL}/api/payments/create-order`, {
    method: "POST",
    body: JSON.stringify({
      order_id: orderId,
      customer_id: customerId || undefined,
    }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Payment order creation failed" }));
    throw new Error(err.detail || `Payment request failed with status ${response.status}`);
  }

  const data: PaymentOrderResponse = await response.json();
  return data;
}
