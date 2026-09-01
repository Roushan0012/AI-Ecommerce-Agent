import { createPaymentOrder, PaymentOrderResponse } from "./api";

declare global {
  interface Window {
    Razorpay?: any;
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

    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

export interface InitiateCheckoutOptions {
  orderId: string;
  customerId?: string;
  name?: string;
  description?: string;
  customerEmail?: string;
  customerPhone?: string;
  onPaymentInitiated?: (paymentOrder: PaymentOrderResponse) => void;
  onModalDismiss?: () => void;
}

/**
 * Initiates Razorpay Test Mode checkout for an application order:
 * 1. Calls backend POST /api/payments/create-order with order_id.
 * 2. Uses backend-authoritative amount, key_id, and razorpay_order_id.
 * 3. Opens the Razorpay Checkout modal in test mode.
 * Note: Payment success verification is strictly deferred to Step 2.11 backend webhooks.
 */
export async function launchRazorpayCheckout(
  options: InitiateCheckoutOptions
): Promise<PaymentOrderResponse> {
  const isLoaded = await loadRazorpayScript();
  if (!isLoaded) {
    throw new Error("Razorpay Checkout SDK failed to load. Please check your network connection.");
  }

  // 1. Fetch authoritative Razorpay order from backend
  const paymentOrder = await createPaymentOrder(options.orderId, options.customerId);

  if (options.onPaymentInitiated) {
    options.onPaymentInitiated(paymentOrder);
  }

  // 2. Configure Razorpay options using backend-supplied values
  const rzpOptions = {
    key: paymentOrder.key_id,
    amount: paymentOrder.amount_in_paise,
    currency: paymentOrder.currency,
    name: options.name || "AI Commerce Agent",
    description: options.description || `Checkout for Order ${paymentOrder.order_id.slice(0, 8)}`,
    order_id: paymentOrder.razorpay_order_id,
    prefill: {
      email: options.customerEmail || "customer@example.com",
      contact: options.customerPhone || "9999999999",
    },
    theme: {
      color: "#0F172A",
    },
    modal: {
      ondismiss: () => {
        if (options.onModalDismiss) {
          options.onModalDismiss();
        }
      },
    },
    handler: (response: any) => {
      // Step 2.10: Client captures the response, but authoritative reconciliation
      // and status update to 'paid' is reserved for Step 2.11 webhooks/verification.
      console.log("Razorpay payment response received:", response);
    },
  };

  const razorpayInstance = new window.Razorpay(rzpOptions);
  razorpayInstance.open();

  return paymentOrder;
}
