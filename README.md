# AI Commerce Agent Platform

> Razorpay AI Buildathon — Track 01: AI Commerce Agent

A production-grade, authoritative e-commerce backend and merchant platform powered by FastAPI, PostgreSQL (Supabase), Razorpay Test Mode payments, security guardrails, an observable audit trail, and an **Agent-to-Agent Commerce** machine-to-machine interface.

---

## Architecture Overview

```
Buyer Agent / Frontend
        ↓
FastAPI Router Gateway
        ↓
Authentication & Guardrails (Phase 12, Phase 15)
        ↓
Core Services (AI Intent, Catalog Search, Recommendations, Cart, Orders, Razorpay)
        ↓
PostgreSQL Database (Transactional Storage & Phase 13 Audit Trail)
        ↓
Phase 14 Merchant Dashboard (Real-Time Analytics & Growth Metrics)
```

---

## Phase Implementation Status

| Phase | Description | Status |
|---|---|---|
| **Phase 2** | FastAPI ↔ Supabase PostgreSQL Connection & Schema | **Complete** |
| **Phase 3** | Product Catalog & Deterministic Seeding | **Complete** |
| **Phase 4** | Semantic & Filtered Product Discovery APIs | **Complete** |
| **Phase 5** | AI Agent Intent Extraction (Mock, OpenAI, Groq) | **Complete** |
| **Phase 6** | AI Intent → Catalog Search & Tools | **Complete** |
| **Phase 7** | Multi-factor Recommendation Engine with Ranking | **Complete** |
| **Phase 8** | Growth Engine: Upsell & Cross-sell Recommendations | **Complete** |
| **Phase 9** | Cart & Order Management Foundation | **Complete** |
| **Phase 10** | Razorpay Payment Integration (Test Mode) | **Complete** |
| **Phase 11** | Razorpay Webhook Signature Verification & Auto-Settlement | **Complete** |
| **Phase 12** | Security & Backend-Authoritative Guardrails | **Complete** |
| **Phase 13** | Observable Agent Audit Trail & Secret Redaction | **Complete** |
| **Phase 14** | Merchant Dashboard & Real-Time Business Analytics | **Complete** |
| **Phase 15** | Agent-to-Agent Commerce (Machine-to-Machine Interface) | **Complete** |
| **Phase 16** | Adversarial Security Regression Suite & Verification | **Complete** |
| **Phase 17A** | JWT Authentication Foundation & Argon2 Hashing | **Complete** |
| **Phase 17B** | User Registration & Login Endpoints | **Complete** |
| **Phase 17C** | JWT Protected APIs & Ownership Verification | **Complete** |

---

## Key Features

### 1. Agent-to-Agent Commerce (Phase 15)
- **Machine-to-Machine Security**: Protected by `X-Agent-Key` header verified in constant time.
- **Untrusted External Agent Model**: Client-provided prices, subtotals, and totals are ignored; all calculations and inventory validations are backend-authoritative.
- **Idempotency**: Repeated checkout requests with the same cart return the existing order safely without duplicate conversions.
- **Payment Boundary**: External agents cannot mark orders as paid; payment confirmation strictly requires HMAC-SHA256 verified Razorpay webhooks.

### 2. Guardrails & Audit Trail (Phases 12 & 13)
- Centralized validation across all sensitive endpoints.
- Redaction of API keys, tokens, and credentials in logs and outputs.
- Comprehensive tracking of `AGENT_REQUEST`, `RECOMMENDATION`, `CART_UPDATED`, `ORDER_CREATED`, and `PAYMENT_EVENT`.

### 3. Merchant Dashboard (Phase 14)
- Real-time revenue, order counts, cart conversion rate, and average order value (AOV).
- AI attribution metrics and growth revenue tracking (upsell and cross-sell).
- Live observable audit feed and order status breakdown.

---

## Running the Platform

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Running Test Suites
```bash
# Pytest (172 tests across all phases)
backend/.venv/bin/pytest backend/tests/ -v

# Postman / Newman (35 live endpoint tests)
npx newman run docs/postman/AI-Commerce-Agent-API.postman_collection.json
```
