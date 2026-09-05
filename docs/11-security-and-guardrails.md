# Security Architecture and Guardrails

## 1. Overview

The AI Commerce Agent Platform implements defense-in-depth across the network, application, database, and operational layers. The security architecture assumes an adversarial operating environment where client applications, web browsers, and external software agents are untrusted entities.

The implementation is located across:
- `backend/app/core/security_middleware.py`
- `backend/app/core/guardrails.py`
- `backend/app/core/logging_security.py`
- `backend/app/core/config.py`
- `backend/app/core/security.py`
- `backend/tests/test_adversarial_security.py`

---

## 2. Threat Model and Defense Matrix

| Threat Category | Potential Attack Vector | Implemented Defense Control | Source Module |
|---|---|---|---|
| Price Tampering | Client submits manipulated unit prices or discount amounts | Server-authoritative calculations; client price submissions are ignored | `cart_service.py`, `order_service.py` |
| Inventory Oversell | Concurrent race condition attempting to purchase more stock than available | Transactional inventory validation and atomic stock decrements | `order_service.py`, `payment_service.py` |
| Timing Attacks | Measuring response time differences to brute-force agent API keys | Constant-time key comparison via `hmac.compare_digest` | `agent_commerce_service.py` |
| Credential Brute Force | High-frequency password-guessing attacks against login routes | Sliding-window IP rate limiting (10-30 req/min) via `slowapi` | `security_middleware.py` |
| Denial of Service (DoS) | Memory exhaustion via massive HTTP request payloads | `RequestSizeLimitMiddleware` enforcing 2MB payload ceiling (`413`) | `security_middleware.py` |
| Privilege Escalation | Submitting `role: "admin"` in public customer registration | Strict role whitelisting; registration hardcodes role to `customer` | `auth_service.py`, `models/user.py` |
| Payment Forgery | Spoofing payment success callbacks or webhooks | Cryptographic HMAC-SHA256 signature verification on callbacks and webhooks | `razorpay_service.py`, `payment_service.py` |
| Webhook Replay | Replaying captured webhook payloads to duplicate order settlement | Idempotent payment processing checking `Payment.status == "paid"` | `payment_service.py` |
| Data Leakage in Logs | Passwords, tokens, or private keys appearing in log sinks | `SensitiveDataRedactionFilter` scrubbing sensitive patterns | `logging_security.py` |
| Clickjacking & MIME Sniffing | Framing web pages or interpreting files as different MIME types | Security headers: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` | `security_middleware.py` |
| Insecure Production Config | Starting production containers with dev placeholder keys | `Settings.validate_production_config()` asserting key entropy | `config.py` |

---

## 3. Implemented Security Controls

### 3.1 Server-Authoritative Financial Integrity
Client requests specifying `price`, `unit_price`, `subtotal`, `discount`, or `total` are disregarded. All prices are resolved by querying `Product.price` in PostgreSQL. All calculations use Python's `Decimal` module:
```python
subtotal = sum(Decimal(str(item.quantity)) * item.unit_price for item in items)
total = max(Decimal("0.00"), subtotal - discount)
```
Orders cannot be placed with negative prices, zero quantities, or negative balances.

### 3.2 In-Memory Sliding-Window Rate Limiting
Implemented via `RateLimitMiddleware` in `app/core/security_middleware.py`:
- Two-Tier Sliding Window:
  - Auth Tier: Applied to `/api/auth/*` routes. Limit is `10 req/min` in production (`30 req/min` in development).
  - Default Tier: Applied to all other endpoints. Limit is `120 req/min` in production (`300 req/min` in development).
- Exceeding the rate limit immediately returns `429 Too Many Requests` accompanied by a `Retry-After: 60` HTTP response header.

### 3.3 Request Body Size Limiting
Configured via `RequestSizeLimitMiddleware`:
- Inspects incoming `Content-Length` headers before reading large streams into memory.
- If `Content-Length > MAX_REQUEST_BODY_BYTES` (default: 2,097,152 bytes / 2MB), the request is aborted with `413 Payload Too Large`.
- Protects the ASGI server from memory-exhaustion denial-of-service attacks.

### 3.4 Defensive HTTP Security Headers
The `SecurityHeadersMiddleware` attaches standard defensive headers to every HTTP response:
```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), camera=(), microphone=()
```
When running in production mode (`is_production == True`), HTTP Strict Transport Security is automatically appended:
```http
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

### 3.5 Cross-Origin Resource Sharing (CORS) Policy
CORS origins are configured via `CORS_ORIGINS`:
- Development defaults allow `http://localhost:3000` and `http://127.0.0.1:3000`.
- In production, `Settings.validate_cors_origins()` validates that origins are explicitly specified. Wildcard origins (`*`) are strictly forbidden when credentials (`allow_credentials=True`) are enabled.

### 3.6 Constant-Time Agent Authentication
Machine agents accessing `/api/agent-commerce/*` must supply an `X-Agent-Key` header. Verification uses constant-time string comparison (`hmac.compare_digest`) rather than standard equality (`==`), ensuring response execution time is independent of how many characters match the secret key:
```python
is_valid = hmac.compare_digest(provided_key, settings.COMMERCE_AGENT_KEY)
```

### 3.7 Sensitive Data Redaction Filter
The platform employs a centralized logging filter (`SensitiveDataRedactionFilter`) in `app/core/logging_security.py` that intercepts all log records across standard loggers. Regex patterns scrub:
- Passwords (`password="***"`, `password_hash="***"`)
- Bearer tokens (`Bearer eyJ...` -> `Bearer [REDACTED]`)
- Agent keys (`ag_live_...` -> `[REDACTED]`)
- Database connection strings with embedded passwords
- Razorpay secret keys

#### 422 Validation Error Redaction
FastAPI request validation errors (`RequestValidationError`) are intercepted by a custom exception handler in `app/main.py`. If a shopper submits an invalid password (e.g., too short), the error response redacts the rejected input value (`"input": "[REDACTED]"`), ensuring sensitive credentials are never reflected in error payloads.

#### 500 Error Masking in Production
In production mode (`ENVIRONMENT=production`), unhandled internal server exceptions return a masked generic message (`{"detail": "An internal server error occurred. Please contact support."}`) to prevent leaking stack traces or database connection details.

### 3.8 Webhook Cryptographic Verification
Inbound Razorpay webhooks (`POST /api/payments/webhook`) capture raw request bytes before JSON parsing and verify the HMAC-SHA256 signature against `RAZORPAY_WEBHOOK_SECRET`. Replay attacks and duplicate deliveries are detected through idempotency checks against the `Payment` and `AuditLog` records.

### 3.9 Production Configuration Validation
During application startup (`lifespan`), `Settings.validate_production_config()` executes if `ENVIRONMENT=production`. It validates:
- `DATABASE_URL` is set and does not use SQLite.
- `JWT_SECRET_KEY` is at least 32 characters and does not match insecure development placeholders.
- `COMMERCE_AGENT_KEY` is at least 16 characters and does not match development placeholders.
- `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET` are configured with production credentials.
- `CORS_ORIGINS` specifies trusted domains without wildcards.
If any parameter fails, the server refuses to start, raising a `ConfigurationError`.

---

## 4. Adversarial Security Test Suite

The security controls are validated by automated adversarial tests in `backend/tests/test_adversarial_security.py`:
- SQL Injection: Tests verify that SQL injection strings (e.g., `' OR '1'='1`) in search queries, category filters, and user emails are safely parameterized and neutralized by SQLAlchemy.
- Price Tampering: Tests submit custom `price` and `total` fields in cart and checkout payloads, confirming that backend services ignore client numbers and charge authoritative amounts.
- Role Escalation: Tests attempt to register accounts with `role: "admin"` and verify that the resulting user is restricted to `customer`.
- Timing Side-Channels: Tests verify that `hmac.compare_digest` is used for all machine key checks.
- Secret Leak Prevention: Tests scan the entire repository tree to ensure zero credentials or private keys are tracked by version control.
