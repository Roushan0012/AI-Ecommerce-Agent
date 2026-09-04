import { createPaymentOrder, PaymentOrderResponse } from "./api";

interface RazorpayInstance {
  open: () => void;
  on?: (event: string, callback: (res: RazorpayFailureResponse) => void) => void;
}

interface RazorpayConstructor {
  new (options: Record<string, unknown>): RazorpayInstance;
}

declare global {
  interface Window {
    Razorpay?: RazorpayConstructor;
  }
}

/**
 * Dynamically loads the Razorpay Standard Checkout JS script.
 */
export function loadRazorpayScript(): Promise<boolean> {
  return new Promise((resolve) => {
    if (typeof window === "undefined") {
      resolve(false);
      return;
    }
    if (window.Razorpay) {
      resolve(true);
      return;
    }
    if (typeof document === "undefined") {
      resolve(false);
      return;
    }

    const existingScript = document.querySelector<HTMLScriptElement>(
      'script[src="https://checkout.razorpay.com/v1/checkout.js"]'
    );
    if (existingScript) {
      existingScript.addEventListener("load", () => resolve(true), { once: true });
      existingScript.addEventListener("error", () => resolve(false), { once: true });
      return;
    }

    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

export interface RazorpaySuccessResponse {
  razorpay_payment_id: string;
  razorpay_order_id: string;
  razorpay_signature?: string;
}

export interface RazorpayFailureResponse {
  error?: {
    code?: string;
    description?: string;
    source?: string;
    step?: string;
    reason?: string;
    metadata?: Record<string, unknown>;
  };
}

export interface InitiateCheckoutOptions {
  orderId: string;
  customerId?: string;
  name?: string;
  description?: string;
  customerEmail?: string;
  customerPhone?: string;
  onPaymentInitiated?: (paymentOrder: PaymentOrderResponse) => void;
  onPaymentSuccess?: (response: RazorpaySuccessResponse, paymentOrder: PaymentOrderResponse) => void;
  onPaymentFailure?: (error: RazorpayFailureResponse) => void;
  onModalDismiss?: () => void;
}

/**
 * Initiates Razorpay Test Mode checkout for an application order:
 * 1. Calls backend POST /api/payments/create-order with order_id.
 * 2. Uses backend-authoritative amount, key_id, and razorpay_order_id.
 * 3. Opens the Razorpay Checkout modal in test mode.
 * Note: Payment success verification is strictly authoritative via backend webhooks/order polling.
 */
export async function launchRazorpayCheckout(
  options: InitiateCheckoutOptions
): Promise<PaymentOrderResponse> {
  if (!options.orderId) {
    throw new Error("Order ID is required to initiate checkout.");
  }

  const isLoaded = await loadRazorpayScript();
  if (!isLoaded) {
    throw new Error("Razorpay Checkout SDK failed to load. Please check your network connection.");
  }

  // 1. Fetch authoritative Razorpay order from backend
  const paymentOrder = await createPaymentOrder(options.orderId, options.customerId);

  if (options.onPaymentInitiated) {
    options.onPaymentInitiated(paymentOrder);
  }

  const keyId =
    paymentOrder.key_id || process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID || "";
  if (!keyId) {
    throw new Error("Razorpay Key ID is not configured. Unable to launch checkout.");
  }

  // 2. Configure Razorpay options using backend-supplied values
  const rzpOptions = {
    key: keyId,
    amount: paymentOrder.amount_in_paise,
    currency: paymentOrder.currency,
    name: options.name || "AI Commerce Store",
    description: options.description || `Order #${paymentOrder.order_id.slice(0, 8)}`,
    order_id: paymentOrder.razorpay_order_id,
    prefill: {
      email: options.customerEmail || "customer@example.com",
      contact: options.customerPhone || "9999999999",
    },
    theme: {
      color: "#4f46e5",
    },
    modal: {
      ondismiss: () => {
        if (options.onModalDismiss) {
          options.onModalDismiss();
        }
      },
    },
    handler: (response: RazorpaySuccessResponse) => {
      if (options.onPaymentSuccess) {
        options.onPaymentSuccess(response, paymentOrder);
      }
    },
  };

  if (!window.Razorpay) {
    throw new Error("Razorpay Checkout SDK is not available on window.");
  }

  const razorpayInstance = new window.Razorpay(rzpOptions);
  if (typeof razorpayInstance.on === "function") {
    razorpayInstance.on("payment.failed", (res: RazorpayFailureResponse) => {
      if (options.onPaymentFailure) {
        options.onPaymentFailure(res);
      }
    });
  }
  razorpayInstance.open();

  return paymentOrder;
}
