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
