# Merchant Dashboard and Business Analytics

## 1. Overview

The Merchant Dashboard provides store operators and administrators with real-time, server-authoritative financial metrics, order tracking, and AI revenue attribution. Unlike client-side analytics tools that rely on browser pixels or estimated tracking, all metrics in the dashboard are computed directly from PostgreSQL database records (`orders`, `carts`, `payments`, and `audit_logs`).

The implementation is located across:
- `backend/app/services/dashboard_service.py`
- `backend/app/api/dashboard.py`
- `backend/app/schemas/dashboard.py`
- `frontend/src/app/dashboard/` (and admin views)

---

## 2. Dashboard Endpoints and Access Control

All dashboard endpoints require the `merchant` or `admin` role via the `require_merchant` dependency:

| Endpoint | Method | Response Schema | Purpose |
|---|---|---|---|
| `/api/dashboard/overview` | `GET` | `OverviewMetricsResponse` | Aggregated revenue, AOV, conversion rate, and AI attribution metrics |
| `/api/dashboard/orders` | `GET` | `DashboardOrdersResponse` | Recent merchant orders with live payment status and AI assistance tags |
| `/api/dashboard/activity` | `GET` | `DashboardActivityResponse` | Recent audit events and agent activity feed |

---

## 3. Metric Calculations and Formulas

### 3.1 Financial Performance
- Total Revenue (`total_revenue`):
  ```sql
  SELECT COALESCE(SUM(total), 0.00) FROM orders WHERE status = 'paid';
  ```
  Sum of all paid order totals in INR.
- Paid Orders Count (`paid_orders_count`): Count of orders with `status = 'paid'`.
- Total Orders Count (`total_orders_count`): Total count of orders across all statuses (`pending_payment`, `paid`, `payment_failed`, `cancelled`).
- Average Order Value (`average_order_value`):
  $$\text{AOV} = \frac{\text{total\_revenue}}{\text{paid\_orders\_count}}$$
  Returns `0.00` if `paid_orders_count == 0`.

### 3.2 Conversion Performance
- Cart-to-Order Conversion Rate (`conversion_rate`):
  $$\text{Conversion Rate} = \left( \frac{\text{paid\_orders\_count}}{\text{total\_carts}} \right) \times 100\%$$
  Measures the percentage of assembled customer carts that culminate in verified purchases.

### 3.3 AI Assistance and Revenue Attribution
The platform links orders to prior AI agent operations through the `audit_logs` table:
- AI Customer Cohort: Identifies customers who executed AI operations (`USER_REQUEST`, `INTENT_DETECTED`, `RECOMMENDATION`, `TOOL_CALL`, `TOOL_RESULT`) prior to checkout.
- AI-Assisted Orders Count (`ai_assisted_orders_count`): Count of paid orders placed by customers in the AI cohort.
- AI-Assisted Revenue (`ai_assisted_revenue`): Sum of paid order totals originating from the AI cohort.
- AI-Assisted Percentage (`ai_assisted_percentage`):
  $$\text{AI Assisted \%} = \left( \frac{\text{ai\_assisted\_orders\_count}}{\text{paid\_orders\_count}} \right) \times 100\%$$

### 3.4 Recommendation and Growth Performance
- Recommendations Generated (`recommendations_generated`): Count of `RECOMMENDATION` audit events.
- Recommendations Accepted (`recommendations_accepted`): Count of paid orders placed by customers who received AI recommendations.
- Recommendation Acceptance Rate (`recommendation_acceptance_rate`):
  $$\text{Acceptance Rate} = \left( \frac{\text{recommendations\_accepted}}{\text{recommendations\_generated}} \right) \times 100\%$$
- Upsell and Cross-Sell Attribution:
  - `upsell_count`: Sum of upgrade items recommended via growth actions.
  - `cross_sell_count`: Sum of companion accessory items recommended via growth actions.
  - `upsell_revenue` and `cross_sell_revenue`: Attributed proportion of growth revenue derived from paid orders in the growth cohort.

---

## 4. Sample API Responses

### `GET /api/dashboard/overview`
```json
{
  "total_revenue": "142597.00",
  "paid_orders_count": 28,
  "total_orders_count": 34,
  "average_order_value": "5092.75",
  "conversion_rate": 62.22,
  "ai_assisted_orders_count": 22,
  "ai_assisted_revenue": "119890.00",
  "ai_assisted_percentage": 78.57,
  "recommendations_generated": 54,
  "recommendations_accepted": 19,
  "recommendation_acceptance_rate": 35.19,
  "upsell_count": 14,
  "upsell_revenue": "43200.00",
  "cross_sell_count": 21,
  "cross_sell_revenue": "28800.00",
  "currency": "INR"
}
```

### `GET /api/dashboard/orders?page=1&page_size=2`
```json
{
  "items": [
    {
      "id": "7b8c9d0e-1f2a-3b4c-5d6e-7f8a9b0c1d2e",
      "customer_id": "u1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
      "total": "7298.00",
      "currency": "INR",
      "status": "paid",
      "payment_status": "paid",
      "items_count": 2,
      "is_ai_assisted": true,
      "created_at": "2026-09-04T12:00:00Z"
    }
  ],
  "total": 28,
  "page": 1,
  "page_size": 2
}
```

### `GET /api/dashboard/activity?limit=2`
```json
{
  "items": [
    {
      "id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
      "event_type": "PAYMENT_EVENT",
      "action": "payment_verified_and_paid",
      "status": "success",
      "customer_id": "u1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
      "cart_id": "c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
      "order_id": "7b8c9d0e-1f2a-3b4c-5d6e-7f8a9b0c1d2e",
      "error_message": null,
      "created_at": "2026-09-04T12:01:30Z"
    }
  ],
  "total": 120
}
```
