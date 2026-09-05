# Razorpay Payment Integration

## 1. Overview

The AI Commerce Agent Platform integrates with the Razorpay Payment Gateway operating in Test Mode (`rzp_test_*`). The integration provides end-to-end payment simulation for Indian Rupee (INR) transactions without moving real funds, covering:
1. Server-authoritative order creation in Razorpay.
2. Client-side modal checkout using Razorpay Checkout.js.
3. Cryptographic HMAC-SHA256 signature verification on payment authorization callbacks.
4. Asynchronous webhook event processing with replay protection and amount reconciliation.
5. Automatic settlement: Order status transition to `paid`, inventory decrement, and active cart cleanup.

The implementation is located across:
- `backend/app/services/razorpay_service.py`
- `backend/app/services/payment_service.py`
- `backend/app/api/payments.py`
- `frontend/src/lib/razorpay.ts`

---

## 2. End-to-End Payment Sequence Diagram

```
Customer              Next.js Frontend            FastAPI Backend             Razorpay Gateway
   |                         |                           |                            |
   |--- 1. Click Checkout -->|                           |                            |
   |                         |-- 2. POST /api/orders --->|                            |
   |                         |                           |-- 3. Verify stock & total  |
   |                         |                           |-- 4. Create internal order |
   |                         |<- 5. Order created -------|                            |
   |                         |                           |                            |
   |                         |-- 6. POST /create-order ->|                            |
   |                         |      (order_id)           |-- 7. Read order.total (DB) |
   |                         |                           |-- 8. Convert to paise      |
   |                         |                           |-- 9. POST /v1/orders ----->|
   |                         |                           |<- 10. rzp_order_id --------|
   |                         |                           |-- 11. Save Payment record  |
   |                         |<- 12. Checkout payload ---|                            |
   |                         |       (key_id, rzp_order, |                            |
   |                         |        amount_in_paise)   |                            |
   |                         |                           |                            |
   |<- 13. Open RZP Modal ---|                           |                            |
   |    (Cards/UPI/Netbank)  |                           |                            |
   |                         |                           |                            |
   |-- 14. Authorize Payment |------------------------------------------------------->|
   |                         |                           |                            |
   |                         |<- 15. Callback handler <--|                            |
   |                         |    (rzp_payment_id,       |                            |
   |                         |     rzp_order_id,         |                            |
   |                         |     rzp_signature)        |                            |
   |                         |                           |                            |
   |                         |-- 16. Webhook (Async) -------------------------------->|
   |                         |                           |<- 17. POST /webhook -------|
   |                         |                           |   (payment.captured event, |
   |                         |                           |    X-Razorpay-Signature)   |
   |                         |                           |                            |
   |                         |                           |-- 18. Verify HMAC-SHA256   |
   |                         |                           |-- 19. Check idempotency    |
   |                         |                           |-- 20. Reconcile amount (DB)|
   |                         |                           |-- 21. Order.status = 'paid'|
   |                         |                           |-- 22. Decrement inventory  |
   |                         |                           |-- 23. Clear active cart    |
   |                         |                           |-- 24. Return 200 OK ------>|
   |                         |                           |                            |
   |                         |-- 25. Check Order status->|                            |
   |<- 26. Show Receipt -----|<- 27. Order is paid ------|                            |
```

---

## 3. Configuration and Test Mode Credentials

All Razorpay interactions are configured through environment variables:
- `RAZORPAY_KEY_ID`: Public key identifier (e.g., `rzp_test_placeholder` in dev/test, or assigned test key). Shared with the frontend for the checkout modal.
- `RAZORPAY_KEY_SECRET`: Private secret key. Kept strictly on the backend; never exposed to the frontend.
- `RAZORPAY_CURRENCY`: Default currency code (`INR`).
- `RAZORPAY_WEBHOOK_SECRET`: Secret used to generate HMAC-SHA256 signatures for webhook validation.

> **Security Rule**: In production mode (`ENVIRONMENT=production`), `Settings.validate_production_config()` strictly prohibits insecure placeholder keys and requires live or valid credentials.

---

## 4. Currency and Smallest-Unit Handling (Paise)

Razorpay requires transaction amounts to be represented in the smallest denomination of the target currency. For Indian Rupees, this is **paise** (`₹1.00 = 100 paise`).

To eliminate floating-point precision errors (e.g., `19.99 * 100 = 1998.9999999999998`), the backend converts currency values using integer rounding:

```python
amount_in_paise = int(round(float(authoritative_amount) * 100))
```

Example conversions:
- `₹4,499.00` -> `449900` paise
- `₹2,799.50` -> `279950` paise
- `₹99.00` -> `9900` paise

---

## 5. Order Creation (`POST /api/payments/create-order`)

1. Request Payload:
   ```json
   {
     "order_id": "7b8c9d0e-1f2a-3b4c-5d6e-7f8a9b0c1d2e",
     "customer_id": "u1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c"
   }
   ```
2. Ownership Validation: Ensures `order.customer_id == current_user.id`.
3. Eligibility Check: Verifies the order is in `pending_payment` or `created` status. Rejects orders that are already `paid` or `cancelled`.
4. Authoritative Lookup: Reads `order.total` directly from the database. Client-submitted prices or amounts in the request are strictly rejected or ignored.
5. Razorpay API Call:
   ```python
   rzp_order = razorpay_client.order.create({
       "amount": amount_in_paise,
       "currency": "INR",
       "receipt": f"rcpt_{order.id.hex[:12]}",
       "notes": {
           "application_order_id": str(order.id),
           "customer_id": str(order.customer_id),
           "environment": "test",
       },
   })
   ```
6. Persistence: Creates a `Payment` record in the database with status `'created'` and links `order.razorpay_order_id = rzp_order["id"]`.
7. Response: Returns `key_id`, `razorpay_order_id`, `amount_in_paise`, and `currency` for modal launch.

---

## 6. Client-Side Modal Execution

The Next.js storefront dynamically loads the Razorpay script (`https://checkout.razorpay.com/v1/checkout.js`) via `frontend/src/lib/razorpay.ts`.

The modal options include:
```typescript
const options = {
  key: key_id,
  amount: amount_in_paise,
  currency: "INR",
  name: "AI Commerce Store",
  description: `Order #${order_id.slice(0, 8)}`,
  order_id: razorpay_order_id,
  prefill: {
    email: userEmail,
  },
  theme: {
    color: "#2563EB",
  },
  handler: function (response) {
    // Callback contains:
    // response.razorpay_payment_id
    // response.razorpay_order_id
    // response.razorpay_signature
  },
};
```

---

## 7. Cryptographic Signature Verification

Razorpay payment integrity is verified using HMAC-SHA256 signatures across two distinct channels:

### 7.1 Client Callback Signature Verification
When the client modal succeeds, Razorpay provides a signature computed as:
```
HMAC_SHA256(razorpay_order_id + "|" + razorpay_payment_id, RAZORPAY_KEY_SECRET)
```
The backend verifies this using the Razorpay utility:
```python
razorpay_client.utility.verify_payment_signature({
    "razorpay_order_id": payload.razorpay_order_id,
    "razorpay_payment_id": payload.razorpay_payment_id,
    "razorpay_signature": payload.razorpay_signature,
})
```

### 7.2 Webhook Signature Verification (`POST /api/payments/webhook`)
Razorpay delivers asynchronous webhook notifications for events such as `payment.captured`, `order.paid`, and `payment.failed`.

1. Raw Body Capture: Webhook verification requires the raw, unparsed request bytes before any JSON deserialization:
   ```python
   body_bytes = await request.body()
   ```
2. Header Extraction: Extracts the `X-Razorpay-Signature` HTTP header. If missing, rejects with `400 Bad Request`.
3. HMAC-SHA256 Verification:
   ```python
   expected_signature = hmac.new(
       key=settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
       msg=body_bytes,
       digestmod=hashlib.sha256,
   ).hexdigest()
   
   is_valid = hmac.compare_digest(expected_signature, x_razorpay_signature)
   ```
4. Constant-Time Comparison: Uses `hmac.compare_digest` to eliminate timing attacks.

---

## 8. Webhook Processing, Amount Reconciliation, and Idempotency

Once the webhook signature is validated, `PaymentService.process_webhook_event()` executes defensive checks:

### 8.1 Database Entity Lookup
Extracts `razorpay_order_id` from the payload and queries the database for the matching `Payment` and `Order` records. If no matching record exists, the event is logged and safely ignored (`status: "ignored"`).

### 8.2 Idempotency and Duplicate Handling
Webhooks may be retried multiple times by the payment gateway due to network timeouts. If `payment.status == "paid"` and a subsequent `payment.captured` or `order.paid` event arrives, the service detects the duplicate:
```python
if payment and payment.status == "paid":
    return {
        "status": "ok",
        "idempotent": True,
        "message": "Payment already verified and marked paid."
    }
```
The endpoint returns `200 OK` immediately without repeating stock decrements or order updates.

### 8.3 Amount and Currency Reconciliation
Before settling an order, the webhook payload amount is reconciled against the authoritative database record:
- Currency check: Rejects with `SECURITY_VIOLATION` if payload currency does not match `payment.currency`.
- Amount check: Computes `expected_amount_in_paise = int(round(float(payment.amount) * 100))`. If `int(payload_amount) != expected_amount_in_paise`, logs a `SECURITY_VIOLATION` audit event, marks `payment.status = "failed"`, and rejects the transaction.

### 8.4 Order Settlement and Stock Decrement
Upon successful reconciliation:
1. `payment.status = "paid"`
2. `order.status = "paid"`
3. Product stock decrement: Iterates through each `OrderItem` and atomically decrements `Product.inventory -= item.quantity`.
4. Cart cleanup: If the customer has an active cart, clears all cart items to prevent duplicate checkout.
5. Audit event: Emits a `PAYMENT_EVENT` with `action="payment_verified_and_paid"`.
