export interface HealthResponse {
  status: string;
  service: string;
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

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

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

export async function fetchDashboardOverview(): Promise<OverviewMetricsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/dashboard/overview`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to load dashboard overview (status ${response.status})`);
  }

  return response.json();
}

export async function fetchDashboardOrders(
  page: number = 1,
  pageSize: number = 10
): Promise<DashboardOrdersResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/dashboard/orders?page=${page}&page_size=${pageSize}`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to load dashboard orders (status ${response.status})`);
  }

  return response.json();
}

export async function fetchDashboardActivity(
  limit: number = 10
): Promise<DashboardActivityResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/dashboard/activity?limit=${limit}`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to load dashboard activity (status ${response.status})`);
  }

  return response.json();
}

export async function createPaymentOrder(
  orderId: string,
  customerId?: string
): Promise<PaymentOrderResponse> {
  const response = await fetch(`${API_BASE_URL}/api/payments/create-order`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
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
