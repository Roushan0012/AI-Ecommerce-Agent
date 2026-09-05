# Authentication and Role-Based Access Control (RBAC)

## 1. Overview

The AI Commerce Agent Platform enforces authentication and role-based access control (RBAC) across all protected resources. The authentication architecture uses modern, memory-hard Argon2id password hashing for credential storage and stateless JSON Web Tokens (JWT) signed via HMAC-SHA256 (`HS256`) for session authorization.

The implementation is located across:
- `backend/app/core/security.py`
- `backend/app/core/dependencies.py`
- `backend/app/services/auth_service.py`
- `backend/app/api/auth.py`
- `frontend/src/lib/auth.ts`

---

## 2. Password Security: Argon2id Hashing

User passwords are encrypted using the Argon2id variant of the Argon2 algorithm via the `argon2-cffi` library. Argon2id combines memory-hardness (defeating GPU/ASIC password-cracking rigs) with resistance against side-channel cache attacks.

### Configuration Parameters
- Time cost (iterations): 2
- Memory cost: 102,400 KiB (100 MiB)
- Parallelism: 8 threads
- Salt length: 16 bytes (cryptographically generated)
- Hash length: 32 bytes

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher(
    time_cost=2,
    memory_cost=102400,
    parallelism=8,
    hash_len=32,
    salt_len=16,
)

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
```

Plaintext passwords and raw hash strings are never printed to stdout, logged to file sinks, or returned in API responses.

---

## 3. JWT Token Specification and Claims

Authentication produces stateless JSON Web Tokens signed with HMAC-SHA256 (`HS256`) using the server secret key `JWT_SECRET_KEY`.

### Standard Token Payload
```json
{
  "sub": "u1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
  "email": "shopper@example.com",
  "role": "customer",
  "iat": 1725450000,
  "exp": 1725453600
}
```

### Claim Definitions
- `sub` (Subject): The user's unique UUID primary key from the `users` table.
- `email`: The user's verified email address.
- `role`: The authorized RBAC role (`customer`, `merchant`, `admin`).
- `iat` (Issued At): UTC Unix timestamp representing token creation.
- `exp` (Expiration): UTC Unix timestamp representing token expiration. Configurable via `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60 minutes).

Tokens are transmitted in the HTTP request header:
```http
Authorization: Bearer <jwt_access_token>
```

---

## 4. Role Hierarchy and Access Control Matrix

The platform defines three authorization roles via `app.models.user.UserRole`:

```
          [admin] --------> Full platform administration & audit visibility
             |
             +---> [merchant] ------> Catalog management & business analytics
                      |
                      +---> [customer] ------> Catalog browsing, cart, checkout, order history
```

### Endpoint Access Matrix

| Router / Path | Method | Purpose | Authentication | Minimum Required Role |
|---|---|---|---|---|
| `/api/auth/register` | `POST` | Public user registration | None (Public) | Any |
| `/api/auth/login` | `POST` | User authentication & token generation | None (Public) | Any |
| `/api/auth/me` | `GET` | Retrieve current user profile | Bearer JWT | Authenticated (`customer`, `merchant`, `admin`) |
| `/api/products` | `GET` | List and search catalog products | None (Public) | Any |
| `/api/products/{id}` | `GET` | View single product details | None (Public) | Any |
| `/api/products` | `POST` | Create new catalog product | Bearer JWT | `merchant`, `admin` |
| `/api/products/{id}` | `PUT` | Update product details / inventory | Bearer JWT | `merchant`, `admin` |
| `/api/products/{id}` | `DELETE`| Remove product from catalog | Bearer JWT | `merchant`, `admin` |
| `/api/agent/understand` | `POST` | Conversational intent extraction | None (Public) | Any |
| `/api/agent/search` | `POST` | Natural language catalog search | None (Public) | Any |
| `/api/agent/recommend` | `POST` | Multi-factor recommendations | None / Optional JWT | Any |
| `/api/agent/growth` | `POST` | Upsell & cross-sell suggestions | None / Optional JWT | Any |
| `/api/cart` | `GET` | View active shopping cart | Bearer JWT | `customer` |
| `/api/cart/items` | `POST` | Add product to active cart | Bearer JWT | `customer` |
| `/api/cart/items/{id}` | `PUT` | Update cart item quantity | Bearer JWT | `customer` |
| `/api/cart/items/{id}` | `DELETE`| Remove product from cart | Bearer JWT | `customer` |
| `/api/cart` | `DELETE`| Empty entire active cart | Bearer JWT | `customer` |
| `/api/orders` | `POST` | Create order from active cart | Bearer JWT | `customer` |
| `/api/orders` | `GET` | List customer order history | Bearer JWT | `customer` |
| `/api/orders/{id}` | `GET` | View order receipt | Bearer JWT | `customer` (own order) or `admin` |
| `/api/payments/create-order`| `POST` | Initialize Razorpay test order | Bearer JWT | `customer` |
| `/api/payments/webhook` | `POST` | Inbound Razorpay webhook callback | `X-Razorpay-Signature` | Razorpay Gateway |
| `/api/dashboard/overview` | `GET` | View merchant revenue metrics | Bearer JWT | `merchant`, `admin` |
| `/api/dashboard/orders` | `GET` | View recent merchant orders | Bearer JWT | `merchant`, `admin` |
| `/api/dashboard/activity` | `GET` | View recent agent/commerce feed | Bearer JWT | `merchant`, `admin` |
| `/api/audit/admin/all` | `GET` | Platform-wide audit logs | Bearer JWT | `admin` |
| `/api/audit/{customer_id}`| `GET` | Customer audit logs | Bearer JWT | `customer` (own logs) or `admin` |
| `/api/admin/system/status` | `GET` | System health and role counts | Bearer JWT | `admin` |
| `/api/admin/audit-logs` | `GET` | System audit logs | Bearer JWT | `admin` |
| `/api/agent-commerce/*` | `POST`/`GET`| Machine-to-machine commerce | `X-Agent-Key` | Authorized Agent |
| `/api/health` | `GET` | API liveness health check | None (Public) | Any |
| `/api/health/database` | `GET` | Database connectivity health check | None (Public) | Any |

---

## 5. Privilege Escalation Prevention

To prevent unauthorized users from elevating their privileges during registration:
1. Hardcoded Role Assignment: The public registration endpoint (`POST /api/auth/register`) strictly sets the newly created user's role to `'customer'`.
2. Input Sanitization: The `UserRegisterRequest` Pydantic schema excludes role fields, and the internal service completely ignores any role parameter passed in the client payload:
   ```python
   new_user = User(
       id=uuid.uuid4(),
       email=payload.email.lower().strip(),
       password_hash=hash_password(payload.password),
       role=UserRole.CUSTOMER.value,  # Enforced customer role
       is_active=True,
   )
   ```
3. Database Validator: The `User` SQLAlchemy model includes a `@validates("role")` method ensuring that direct database writes validate against `UserRole.values()`.
4. Role Elevation Path: Merchant and administrator roles can only be granted by database administrators via initial migration seeds or controlled direct database administration.

---

## 6. Authentication Dependency Chain

FastAPI route handlers enforce authentication and permissions through composable dependencies defined in `backend/app/core/dependencies.py`:

```python
# 1. Base Token Extraction & User Identity Verification
def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    token = credentials.credentials
    payload = decode_jwt_token(token)
    user_id = payload.get("sub")
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid or inactive user.")
    return user

# 2. Role Authorizers
def require_customer(current_user: User = Depends(get_current_user)) -> User:
    # Any authenticated user possesses customer privileges
    return current_user

def require_merchant(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in [UserRole.MERCHANT.value, UserRole.ADMIN.value]:
        raise HTTPException(status_code=403, detail="Merchant permissions required.")
    return current_user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Administrator permissions required.")
    return current_user
```

---

## 7. Customer Ownership Verification

For resources owned by a specific customer (such as carts, orders, and individual audit logs), RBAC is supplemented by **ownership checks**:
- Cart Access: The cart endpoint reads `current_user.id` directly from the authenticated JWT token. A customer cannot query another user's cart.
- Order Access: When requesting `GET /api/orders/{order_id}`, the service checks:
  ```python
  if current_user.role == UserRole.CUSTOMER.value and order.customer_id != current_user.id:
      raise HTTPException(status_code=404, detail="Order not found.")
  ```
  Returning `404 Not Found` rather than `403 Forbidden` prevents malicious actors from guessing valid order UUIDs through ID enumeration.
- Audit Log Access: `GET /api/audit/{customer_id}` allows access only if `customer_id == current_user.id` or if `current_user.role == "admin"`.
