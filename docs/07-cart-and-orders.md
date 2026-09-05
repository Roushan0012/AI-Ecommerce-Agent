# Cart and Order Management

## 1. Overview

The platform implements a server-authoritative cart and order lifecycle. Client applications (browsers and autonomous software agents) are strictly prohibited from calculating or submitting unit prices, discounts, line totals, or final balances. All financial calculations and inventory allocations are performed exclusively by backend services within transactional database boundaries.

The core services handling this functionality are:
- `backend/app/services/cart_service.py`
- `backend/app/services/order_service.py`
- `backend/app/api/cart.py`
- `backend/app/api/orders.py`

---

## 2. Server-Authoritative Pricing Rationale

Allowing client applications to submit prices or totals introduces critical security and financial vulnerabilities:
- Price Tampering: An attacker or rogue script could alter the DOM, intercept HTTP traffic, or craft a custom payload that specifies `price: 1.00` for an expensive product.
- Stale Catalog Data: Cached client-side prices may differ from recent store adjustments, promotions, or supplier cost updates.
- Inconsistent Rounding: Discrepancies in floating-point math across browsers or devices can lead to currency reconciliation failures at the payment gateway.

To prevent these issues, the client submits only two identifiers: `product_id` (UUID) and `quantity` (positive integer). The backend resolves the price directly from the PostgreSQL `Product` table and performs exact arithmetic using Python's `Decimal` module.

---

## 3. Cart Lifecycle and Operations

```
[Customer / Session]
        |
        +---> GET /api/cart ---------------> Retrieves active cart or creates new active cart
        |
        +---> POST /api/cart/items --------> Adds product; validates inventory; recalculates totals
        |
        +---> PUT /api/cart/items/{id} ----> Updates quantity; verifies stock ceiling
        |
        +---> DELETE /api/cart/items/{id} -> Removes item; recalculates totals
        |
        +---> DELETE /api/cart ------------> Clears all items; resets totals to 0.00
```

### 3.1 Cart Retrieval / Creation (`GET /api/cart`)
- Queries the `carts` table for an existing record where `customer_id == current_user.id` and `status == 'active'`.
- If no active cart exists, creates a new `Cart` record with initial totals of `0.00` INR and commits it to the database.

### 3.2 Adding Items (`POST /api/cart/items`)
1. Guardrail Validation: Checks `quantity > 0`.
2. Authoritative Product Validation:
   - Queries `Product` by ID.
   - Verifies `product.is_active == True`.
   - Verifies `product.inventory > 0`.
3. Inventory Check:
   - If item already exists in cart, calculates `new_quantity = existing.quantity + quantity`.
   - If `new_quantity > product.inventory`, rejects request with `400 Bad Request` citing current available inventory.
4. Total Recalculation:
   - Sets `CartItem.unit_price = product.price`.
   - Sets `CartItem.total_price = Decimal(quantity) * product.price`.
   - Computes `cart.subtotal = sum(item.total_price for item in cart.items)`.
   - Computes `cart.total = max(0.00, cart.subtotal - cart.discount)`.
5. Audit Event: Emits a `CART_UPDATED` event to the `audit_logs` table.

### 3.3 Updating Item Quantity (`PUT /api/cart/items/{product_id}`)
- Adjusts quantity for the specified product.
- Validates the new quantity against current `Product.inventory`.
- Recalculates cart totals and emits audit log.

### 3.4 Removing Items and Clearing Cart
- `DELETE /api/cart/items/{product_id}`: Removes the single item, deletes the `CartItem` row, and recomputes cart totals.
- `DELETE /api/cart`: Deletes all `CartItem` rows associated with the active cart and resets `subtotal`, `discount`, and `total` to `0.00`.

---

## 4. Order Creation and Checkout Pipeline

When a customer or agent initiates checkout (`POST /api/orders`), the cart is atomically converted into an `Order`:

```
[Active Cart with Items]
           |
           v
[OrderService.create_order_from_cart()]
   1. Locate active cart for customer
   2. Verify cart is not empty
   3. Begin Database Transaction
   4. Revalidate all items against live DB:
      - Product exists
      - Product is active
      - item.quantity <= product.inventory
   5. Capture immutable snapshots:
      - OrderItem.product_name = product.name
      - OrderItem.sku = product.sku
      - OrderItem.unit_price = product.price
      - OrderItem.total_price = quantity * product.price
   6. Create Order record:
      - status = 'pending_payment'
      - subtotal = calculated_subtotal
      - total = max(0.00, subtotal - discount)
   7. Mark cart.status = 'converted'
   8. Commit transaction (or Rollback on error)
           |
           v
[Order Created: Status pending_payment]
```

---

## 5. Order State Machine

The order lifecycle is governed by an explicit finite state machine:

```
                  +-------------------------+
                  |      CART CHECKOUT      |
                  +-------------------------+
                               |
                               v
                 +---------------------------+
                 | status: pending_payment   |
                 | - Inventory revalidated   |
                 | - Immutable snapshots set |
                 +---------------------------+
                               |
            +------------------+------------------+
            |                                     |
            v                                     v
+-------------------------+           +-------------------------+
| status: paid            |           | status: payment_failed  |
| - Payment verified via  |           | - Payment rejected,     |
|   HMAC-SHA256 signature |           |   dismissed, or failed  |
| - Inventory decremented |           | - Inventory untouched   |
| - Active cart cleared   |           | - Retry permitted       |
+-------------------------+           +-------------------------+
            |
            v (Administrative / Customer cancellation)
+-------------------------+
| status: cancelled       |
| - Inventory restocked   |
+-------------------------+
```

### State Definitions
- `pending_payment`: The order has been initialized and validated. Stock has been verified but not yet decremented. The order is eligible for payment checkout.
- `paid`: The payment gateway callback or webhook signature was cryptographically verified. Physical product inventory is decremented, and the order is ready for fulfillment.
- `payment_failed`: Payment was declined by the bank or the customer aborted the transaction. Product inventory remains untouched. The customer can retry payment.
- `cancelled`: The order was cancelled prior to shipping. If previously paid, product inventory is incremented back into available stock.

---

## 6. Order Ownership and Security Boundaries

All order retrieval endpoints enforce strict ownership checks:
- `GET /api/orders`: Queries only orders where `Order.customer_id == current_user.id`. A customer can never view another customer's order history.
- `GET /api/orders/{order_id}`: If the requesting user has the `customer` role, the service validates `order.customer_id == current_user.id`. If a customer attempts to access another user's order ID, the endpoint responds with `404 Not Found` (preventing ID enumeration). Users with the `admin` role are permitted to view any order for customer support purposes.

---

## 7. Receipts and Order Details

The endpoint `GET /api/orders/{order_id}` returns a comprehensive itemized receipt:

```json
{
  "id": "7b8c9d0e-1f2a-3b4c-5d6e-7f8a9b0c1d2e",
  "merchant_id": "m1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
  "customer_id": "u1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
  "cart_id": "c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
  "status": "paid",
  "currency": "INR",
  "subtotal": "7298.00",
  "discount": "0.00",
  "total": "7298.00",
  "items": [
    {
      "id": "i1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
      "order_id": "7b8c9d0e-1f2a-3b4c-5d6e-7f8a9b0c1d2e",
      "product_id": "p1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
      "product_name": "Keychron K2 Mechanical Keyboard",
      "sku": "ACC-KB-K2",
      "unit_price": "4499.00",
      "quantity": 1,
      "total_price": "4499.00",
      "created_at": "2026-09-04T12:00:00Z"
    },
    {
      "id": "i2a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
      "order_id": "7b8c9d0e-1f2a-3b4c-5d6e-7f8a9b0c1d2e",
      "product_id": "p2a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
      "product_name": "Logitech Lift Vertical Ergonomic Mouse",
      "sku": "ACC-PG-LIFT",
      "unit_price": "2799.00",
      "quantity": 1,
      "total_price": "2799.00",
      "created_at": "2026-09-04T12:00:00Z"
    }
  ],
  "created_at": "2026-09-04T12:00:00Z",
  "updated_at": "2026-09-04T12:01:30Z"
}
```

---

## 8. Frontend Storefront Experience

In `frontend/src/app/page.tsx`:
- Cart Drawer: Slide-out drawer displaying all items in the active cart, unit prices, quantity increment/decrement buttons, item deletion, and live subtotal calculation.
- Checkout Action: Converts the active cart into an order via `POST /api/orders` and launches the Razorpay payment modal.
- Customer Order History View: A dedicated view accessed via the navigation header or post-checkout confirmation. Displays historical orders with status badges (`Pending Payment`, `Paid`, `Cancelled`), timestamps, and total amounts.
- View Receipt Modal: Drill-down modal rendering an authoritative, itemized receipt breakdown for any historical order.
