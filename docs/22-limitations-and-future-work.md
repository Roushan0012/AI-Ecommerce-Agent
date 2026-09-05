# System Limitations and Future Roadmap

## 1. Overview

To maintain engineering transparency and factual integrity, this document details the verified operational boundaries of the AI Commerce Agent Platform in its current implementation, alongside planned architectural improvements.

---

## 2. Current System Limitations

The following boundaries reflect the current state of the platform as implemented in code:

### 2.1 Razorpay Test Mode Processing
- Current Behavior: All payment operations operate exclusively in Razorpay Test Mode using `rzp_test_*` credentials.
- Boundary: No real fiat monetary transactions occur. Live monetary settlement requires completing Razorpay merchant KYC onboarding, signing banking agreements, and injecting live production keys (`rzp_live_*`).

### 2.2 Single-Store Merchant Model
- Current Behavior: The relational schema includes a `merchants` table, and every product and order references a `merchant_id`.
- Boundary: The customer storefront interface is configured as a single-merchant operational model. It does not currently support multi-vendor shopping carts where products from multiple independent merchants are split, fulfilled separately, or disbursed across independent merchant bank accounts.

### 2.3 Deterministic AI Heuristics vs. Large Language Models
- Current Behavior: The default intent classification and recommendation engines rely on deterministic regular expressions and weighted multi-factor scoring functions (`MockAIProvider`, `RecommendationService`).
- Advantages: Zero external API latency, zero runtime token cost, zero risk of LLM hallucinations, and zero transmission of customer queries to third-party AI APIs.
- Boundary: The system lacks open-ended, multi-turn conversational dialogue memory. Complex conversational negotiations (e.g., "Compare this with the other model you showed me five minutes ago") are not retained across multi-turn sessions unless explicitly re-stated in the query.

### 2.4 Human-in-the-Loop Payment Authorization in A2A Commerce
- Current Behavior: The Agent-to-Agent (A2A) protocol enables external autonomous software agents to query catalogs, assemble carts, and programmatically initialize checkout sessions.
- Boundary: The agent receives a Razorpay checkout reference and payment link that requires explicit customer authorization. The platform deliberately does not support autonomous credit card debiting or unrestricted pre-authorized bank withdrawals without human oversight.

### 2.5 In-Memory Rate Limiting Scope
- Current Behavior: Rate limiting is enforced via `slowapi` using in-memory sliding windows.
- Boundary: In a horizontally scaled production deployment with multiple independent backend container replicas, in-memory rate limiting applies per container instance rather than globally across the cluster. A distributed Redis-backed rate limiting backend would be required for unified cluster-wide throttling.

---

## 3. Future Architectural Roadmap

The following enhancements represent planned architectural evolutions:

### 3.1 Vector Similarity Search (Hybrid Dense-Sparse Retrieval)
- Objective: Enhance conversational product discovery by augmenting keyword filtering with vector embeddings.
- Proposed Architecture: Integrate the `pgvector` extension directly within the existing Supabase PostgreSQL database. Compute dense vector embeddings for product titles and descriptions, executing cosine similarity search alongside lexical filters.

### 3.2 Multi-Vendor Marketplace Support and Split Payouts
- Objective: Allow multiple independent merchants to list inventory on a unified platform.
- Proposed Architecture: Implement cart partitioning by `merchant_id` during checkout, utilizing **Razorpay Route** to automatically split customer payments, deduct platform commissions, and route net proceeds to vendor bank accounts.

### 3.3 Pluggable LLM Sidecar Adapters
- Objective: Enable deep multi-turn conversational shopping dialogues and dynamic price negotiation.
- Proposed Architecture: Introduce pluggable sidecar connectors for local or cloud LLM engines (e.g., local Ollama instances, OpenAI GPT-4o, Anthropic Claude) operating within an isolated dialogue container that forwards structured intent tools to the core commerce API.

### 3.4 Real-Time WebSockets for Live Inventory and Order Tracking
- Objective: Stream live inventory changes and payment state transitions to connected clients.
- Proposed Architecture: Implement FastAPI WebSocket endpoints or Server-Sent Events (SSE) broadcasting real-time inventory decrement events when stock levels shift, eliminating polling delays on the storefront.

### 3.5 Automated Refund and Dispute Workflows
- Objective: Programmatic returns and refund processing.
- Proposed Architecture: Add `/api/payments/refund` endpoints integrated with Razorpay Refund APIs, enabling authorized merchants or customer support agents to trigger partial or full refunds directly through the dashboard.
