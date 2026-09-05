# Frontend Architecture and User Experience

## 1. Overview

The customer storefront is implemented as a modern single-page application built on **Next.js 16.3.3** using the **App Router**, **React 19.2.8**, **TypeScript 5**, and **Tailwind CSS v4**. It features an interactive AI Shopping Assistant, responsive product grid, slide-out cart drawer, Razorpay Checkout modal, and customer order history.

The frontend source is organized as follows:
- `frontend/src/app/page.tsx`: Core single-page storefront integrating catalog browsing, assistant modes, cart drawer, and checkout.
- `frontend/src/app/layout.tsx`: Root HTML shell, fonts, and global metadata.
- `frontend/src/app/globals.css`: Global styles and Tailwind v4 imports.
- `frontend/src/lib/api.ts`: Centralized typed API client communicating with the FastAPI backend.
- `frontend/src/lib/auth.ts`: Client-side JWT management, token expiration checking, and user profile persistence.
- `frontend/src/lib/razorpay.ts`: Dynamic script loader and client modal orchestrator for Razorpay Checkout.

---

## 2. Component and Application Architecture

```
+-------------------------------------------------------------------------------+
|                            ROOT LAYOUT (layout.tsx)                           |
|                                                                               |
|   +-----------------------------------------------------------------------+   |
|   | NAVIGATION HEADER                                                     |   |
|   | - Brand Logo & Store Name                                             |   |
|   | - User Auth Indicator (Sign In / Register / Sign Out)                |   |
|   | - Order History Button                                                |   |
|   | - Cart Drawer Toggle (with live badge counter)                        |   |
|   +-----------------------------------------------------------------------+   |
|                                                                               |
|   +-----------------------------------------------------------------------+   |
|   | AI SHOPPING ASSISTANT BAR                                             |   |
|   | - Query Input Field (natural language prompt)                         |   |
|   | - Mode Switcher:                                                      |   |
|   |   [Smart Search]  |  [Top AI Picks]  |  [Upgrades & Accessories]      |   |
|   +-----------------------------------------------------------------------+   |
|                                                                               |
|   +-----------------------------------------------------------------------+   |
|   | DYNAMIC RESULTS / CATALOG VIEW                                        |   |
|   |                                                                       |   |
|   | - In Search Mode: Standard Product Card Grid (Filtering & Pagination) |   |
|   | - In Recommend Mode: Scored Recommendation Cards (Score + Rationale)  |   |
|   | - In Growth Mode: Primary Item + Upsell Cards + Cross-Sell Companions |   |
|   +-----------------------------------------------------------------------+   |
|                                                                               |
|   +-----------------------------+   +-------------------------------------+   |
|   | SLIDE-OUT CART DRAWER       |   | MODALS                              |   |
|   | - Line items list           |   | - Product Detail Modal              |   |
|   | - Quantity controls (+ / -) |   | - Razorpay Payment Modal            |   |
|   | - Server totals calculation |   | - Order Confirmation / Receipt View |   |
|   | - Checkout Trigger Button   |   | - Auth Sign-In / Register Modal     |   |
|   +-----------------------------+   +-------------------------------------+   |
+-------------------------------------------------------------------------------+
```

---

## 3. The Three AI Assistant Modes Explained

The AI Shopping Assistant features a three-mode toggle allowing shoppers to tailor their product discovery strategy:

### 3.1 Mode 1: Smart Search (`ai-mode-search-btn`)
- Purpose: Conversational search and constraint extraction.
- How It Works: The shopper types an unconstrained query (e.g., "fast charger for laptop under 2000"). The backend parses the query into a structured `ShoppingIntent` (category `Chargers & Cables`, max price `₹2,000`, keywords `fast charger laptop`), queries the database, and returns standard product cards matching those criteria.
- When to Use: Initial exploration when the shopper has broad or specific criteria but wants to browse the general catalog.

### 3.2 Mode 2: Top AI Picks / Recommend for Me (`ai-mode-recommend-btn`)
- Purpose: Multi-factor scored ranking with explainability.
- How It Works: Dispatches `POST /api/agent/recommend`. The backend scores candidate products across category alignment (30%), keyword relevance (35%), price proximity (20%), and inventory health (15%).
- Visual Features:
  - Score Badge: Shows a prominent match percentage (e.g., `88% Match`) derived from the backend composite score.
  - Explainability Rationale: Renders transparent justification tags beneath the title (e.g., *"Matches category 'Computer Accessories'; within budget (₹2,799 <= ₹3,000); available in stock (45 units)"*).
- When to Use: When the shopper wants curated recommendations ranked by overall value rather than standard search results.

### 3.3 Mode 3: Upgrades & Accessories (`ai-mode-growth-btn`)
- Purpose: Contextual upsell and cross-sell suggestions.
- How It Works: Dispatches `POST /api/agent/growth`. The backend identifies a primary product matching the prompt and presents:
  - Upsell Section: Higher-tier alternatives within the same category offering upgraded specifications (e.g., higher wattage, aluminum construction, active noise cancellation) within a bounded price jump.
  - Cross-Sell Section: Recommended accessories and companion hardware based on category affinity mappings (e.g., pairing a keyboard with an ergonomic mouse and felt desk mat).
- Visual Features: Distinct upgrade badges, specification comparison notes, pairing rationales, and independent Add-to-Cart buttons for every suggested item.
- When to Use: When evaluating a specific item and looking for potential upgrades or necessary accessories before proceeding to checkout.

---

## 4. Client State and Authentication Management

Authentication state is managed by `frontend/src/lib/auth.ts`:
- Storage: Access tokens are persisted in browser `localStorage` under the key `ai_commerce_access_token`.
- User Profile: User details (`id`, `email`, `role`) are cached under `ai_commerce_user`.
- Token Expiration: `isTokenExpired(token)` decodes the base64 JWT payload without external libraries and compares the `exp` claim against `Date.now() / 1000`.
- 401 Interception: The `authFetch()` wrapper intercepts `401 Unauthorized` responses and automatically invokes `clearAuth()`, purging stale credentials and updating the UI state.
- Security Boundary: The frontend has zero access to `COMMERCE_AGENT_KEY`, `X-Agent-Key`, or backend secrets.

---

## 5. Storefront Features and Flows

### 5.1 Product Catalog and Details Modal
- Product Grid: Renders responsive cards displaying product image preview, title, category, price formatted in INR (`₹`), and inventory status.
- View Details Modal: Clicking "View Details" queries `GET /api/products/{id}` to display high-resolution imagery, full descriptions, and technical attributes (JSONB). Shoppers can select quantities and add items directly to the cart.

### 5.2 Slide-Out Cart Drawer
- Access: Toggled via the cart icon in the navigation header. Displays a live badge counter reflecting total item count.
- Item Management:
  - Increment / Decrement: Adjusts quantities via `PUT /api/cart/items/{product_id}`.
  - Remove: Deletes items via `DELETE /api/cart/items/{product_id}`.
- Authoritative Pricing Display: Displays subtotal, applied discounts, shipping cost, and final total calculated exclusively by the backend.

### 5.3 Checkout and Razorpay Modal
- Checkout Action: The shopper clicks "Proceed to Checkout". The frontend calls `POST /api/orders` to assemble the order.
- Razorpay Launch: The frontend calls `POST /api/payments/create-order`, receives `razorpay_order_id` and `amount_in_paise`, and opens the Razorpay Checkout JS modal.
- Payment Completion: Upon test payment authorization, the modal callback triggers verification, transitions the order to `paid`, and redirects the user to the order confirmation view.

### 5.4 Customer Order History and Receipt View
- Order List: Accessible from the navigation bar. Queries `GET /api/orders` and renders historical orders with status badges (`Pending Payment`, `Paid`, `Cancelled`), timestamps, and total amounts.
- Receipt Modal: Clicking "View Receipt" queries `GET /api/orders/{id}` and displays a comprehensive receipt containing:
  - Unique Order Reference UUID
  - Creation and payment timestamps
  - Itemized line items: SKU, Product Name, Unit Price, Quantity, Line Subtotal
  - Grand total and currency
  - Payment transaction status

---

## 6. UI States: Loading, Error, and Empty Handling

- Loading States: Dynamic skeleton screens and spinner indicators prevent layout shifts during catalog queries, recommendation scoring, and cart updates.
- Error States: Network or server failures render user-friendly, non-technical error banners with retry buttons.
- Empty States:
  - Empty Search: Renders helpful suggestions if no products match the query.
  - Empty Cart: Renders an empty cart illustration and a button directing the user back to catalog browsing.
  - Empty Order History: Displays guidance encouraging the user to explore the catalog and make their first purchase.
