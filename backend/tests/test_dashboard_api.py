import json
import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.core.seed import seed_catalog
from app.main import app
from app.models.audit_log import AuditLog
from app.models.cart import Cart
from app.models.order import Order
from app.models.payment import Payment
from app.models.product import Product
from app.schemas.audit import AuditEventType
from app.services.audit_service import audit_service
from app.services.dashboard_service import dashboard_service


def get_test_app_client():
    """Create test client with in-memory SQLite database seeded with catalog data."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        seed_catalog(session)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client, engine


# ==========================================
# 1. Overview Metrics & Zero-state Handling
# ==========================================

def test_dashboard_overview_zero_state():
    """1. Empty database returns zero metrics safely without division-by-zero errors."""
    client, engine = get_test_app_client()

    res = client.get("/api/dashboard/overview")
    assert res.status_code == 200
    data = res.json()

    assert float(data["total_revenue"]) == 0.0
    assert data["paid_orders_count"] == 0
    assert data["total_orders_count"] == 0
    assert float(data["average_order_value"]) == 0.0
    assert data["conversion_rate"] == 0.0
    assert data["ai_assisted_orders_count"] == 0
    assert float(data["ai_assisted_revenue"]) == 0.0
    assert data["ai_assisted_percentage"] == 0.0
    assert data["recommendations_generated"] == 0
    assert data["recommendations_accepted"] == 0
    assert data["currency"] == "INR"


def test_dashboard_overview_with_paid_orders():
    """2. Overview metrics calculate authoritative revenue, AOV, and conversion rate."""
    client, engine = get_test_app_client()
    customer_id = str(uuid.uuid4())

    with Session(engine) as session:
        prod = session.query(Product).first()
        prod_id = str(prod.id)
        prod_price = prod.price

    # 1. Add item to cart
    client.post(f"/api/cart/{customer_id}/items", json={"product_id": prod_id, "quantity": 2})

    # 2. Create order
    order_res = client.post("/api/orders", json={"customer_id": customer_id})
    assert order_res.status_code == 201
    order_id = order_res.json()["id"]

    # 3. Simulate payment paid
    with Session(engine) as session:
        order = session.query(Order).filter_by(id=uuid.UUID(order_id)).one()
        order.status = "paid"
        pay = Payment(
            id=uuid.uuid4(),
            order_id=order.id,
            razorpay_order_id="order_test_123",
            amount=order.total,
            currency="INR",
            status="paid",
        )
        session.add(pay)
        session.commit()

    # Query dashboard overview
    res = client.get("/api/dashboard/overview")
    assert res.status_code == 200
    data = res.json()

    expected_revenue = float(prod_price * 2)
    assert float(data["total_revenue"]) == expected_revenue
    assert data["paid_orders_count"] == 1
    assert data["total_orders_count"] == 1
    assert float(data["average_order_value"]) == expected_revenue
    assert data["conversion_rate"] == 100.0


def test_dashboard_overview_ignores_unpaid_and_cancelled_orders():
    """3. Pending and cancelled orders do NOT contribute to revenue or paid order counts."""
    client, engine = get_test_app_client()
    cust_1 = str(uuid.uuid4())
    cust_2 = str(uuid.uuid4())

    with Session(engine) as session:
        prod = session.query(Product).first()
        prod_id = str(prod.id)

    # Order 1 (pending)
    client.post(f"/api/cart/{cust_1}/items", json={"product_id": prod_id, "quantity": 1})
    client.post("/api/orders", json={"customer_id": cust_1})

    # Order 2 (cancelled)
    client.post(f"/api/cart/{cust_2}/items", json={"product_id": prod_id, "quantity": 1})
    order_2 = client.post("/api/orders", json={"customer_id": cust_2}).json()
    with Session(engine) as session:
        o = session.query(Order).filter_by(id=uuid.UUID(order_2["id"])).one()
        o.status = "cancelled"
        session.commit()

    res = client.get("/api/dashboard/overview")
    assert res.status_code == 200
    data = res.json()

    assert float(data["total_revenue"]) == 0.0
    assert data["paid_orders_count"] == 0
    assert data["total_orders_count"] == 2
    assert float(data["average_order_value"]) == 0.0


# ==========================================
# 2. AI Attribution & Growth Metrics
# ==========================================

def test_dashboard_ai_assisted_attribution():
    """4. Attributes orders to AI-assisted commerce when customer used AI agent interactions."""
    client, engine = get_test_app_client()
    customer_id = str(uuid.uuid4())

    with Session(engine) as session:
        prod = session.query(Product).first()
        prod_id = str(prod.id)

    # Record AI agent interaction for this customer
    with Session(engine) as session:
        audit_service.record_event(
            db=session,
            event_type="USER_REQUEST",
            customer_id=uuid.UUID(customer_id),
            action="agent_recommend",
            payload={"query": "noise cancelling headphones"},
        )

    # Customer adds to cart and completes purchase
    client.post(f"/api/cart/{customer_id}/items", json={"product_id": prod_id, "quantity": 1})
    order_res = client.post("/api/orders", json={"customer_id": customer_id}).json()

    with Session(engine) as session:
        order = session.query(Order).filter_by(id=uuid.UUID(order_res["id"])).one()
        order.status = "paid"
        session.commit()

    res = client.get("/api/dashboard/overview")
    assert res.status_code == 200
    data = res.json()

    assert data["paid_orders_count"] == 1
    assert data["ai_assisted_orders_count"] == 1
    assert data["ai_assisted_percentage"] == 100.0
    assert float(data["ai_assisted_revenue"]) == float(order_res["total"])


def test_dashboard_recommendation_performance():
    """5. Tracks recommendations generated and conversion rate."""
    client, engine = get_test_app_client()
    customer_id = str(uuid.uuid4())

    with Session(engine) as session:
        prod = session.query(Product).first()
        prod_id = str(prod.id)

        # 2 recommendation events generated
        audit_service.record_event(
            db=session,
            event_type="RECOMMENDATION",
            customer_id=uuid.UUID(customer_id),
            action="recommend_products",
            result={"recommendation_count": 3},
        )
        audit_service.record_event(
            db=session,
            event_type="RECOMMENDATION",
            customer_id=uuid.uuid4(),  # other customer who didn't buy
            action="recommend_products",
            result={"recommendation_count": 3},
        )

    # Customer converts
    client.post(f"/api/cart/{customer_id}/items", json={"product_id": prod_id, "quantity": 1})
    order_res = client.post("/api/orders", json={"customer_id": customer_id}).json()

    with Session(engine) as session:
        order = session.query(Order).filter_by(id=uuid.UUID(order_res["id"])).one()
        order.status = "paid"
        session.commit()

    res = client.get("/api/dashboard/overview")
    assert res.status_code == 200
    data = res.json()

    assert data["recommendations_generated"] == 2
    assert data["recommendations_accepted"] == 1
    assert data["recommendation_acceptance_rate"] == 50.0


def test_dashboard_upsell_and_cross_sell_metrics():
    """6. Calculates upsell and cross-sell metrics from growth engine events."""
    client, engine = get_test_app_client()
    customer_id = str(uuid.uuid4())

    with Session(engine) as session:
        prod = session.query(Product).first()
        prod_id = str(prod.id)

        # Log growth event
        audit_service.record_event(
            db=session,
            event_type="RECOMMENDATION",
            customer_id=uuid.UUID(customer_id),
            action="growth_recommendations",
            result={"upsells_count": 2, "cross_sells_count": 3},
        )

    # Customer converts
    client.post(f"/api/cart/{customer_id}/items", json={"product_id": prod_id, "quantity": 1})
    order_res = client.post("/api/orders", json={"customer_id": customer_id}).json()

    with Session(engine) as session:
        order = session.query(Order).filter_by(id=uuid.UUID(order_res["id"])).one()
        order.status = "paid"
        session.commit()

    res = client.get("/api/dashboard/overview")
    assert res.status_code == 200
    data = res.json()

    assert data["upsell_count"] == 2
    assert data["cross_sell_count"] == 3
    assert float(data["upsell_revenue"]) > 0.0
    assert float(data["cross_sell_revenue"]) > 0.0


# ==========================================
# 3. Recent Orders & Activity Endpoints
# ==========================================

def test_dashboard_recent_orders_endpoint():
    """7. GET /api/dashboard/orders returns paginated orders with payment statuses."""
    client, engine = get_test_app_client()
    customer_id = str(uuid.uuid4())

    with Session(engine) as session:
        prod = session.query(Product).first()
        prod_id = str(prod.id)

    client.post(f"/api/cart/{customer_id}/items", json={"product_id": prod_id, "quantity": 1})
    client.post("/api/orders", json={"customer_id": customer_id})

    res = client.get("/api/dashboard/orders?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["customer_id"] == customer_id
    assert item["status"] == "pending_payment"
    assert item["items_count"] == 1


def test_dashboard_recent_orders_ai_flag():
    """8. Verifies is_ai_assisted boolean is correctly assigned to recent orders."""
    client, engine = get_test_app_client()
    cust_ai = str(uuid.uuid4())
    cust_direct = str(uuid.uuid4())

    with Session(engine) as session:
        prod = session.query(Product).first()
        prod_id = str(prod.id)

        # AI interaction for cust_ai
        audit_service.record_event(
            db=session,
            event_type="INTENT_DETECTED",
            customer_id=uuid.UUID(cust_ai),
            action="understand_intent",
        )

    # Both customers place orders
    client.post(f"/api/cart/{cust_ai}/items", json={"product_id": prod_id, "quantity": 1})
    client.post("/api/orders", json={"customer_id": cust_ai})

    client.post(f"/api/cart/{cust_direct}/items", json={"product_id": prod_id, "quantity": 1})
    client.post("/api/orders", json={"customer_id": cust_direct})

    res = client.get("/api/dashboard/orders?page=1&page_size=10")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 2

    # Map by customer_id
    order_map = {item["customer_id"]: item for item in items}
    assert order_map[cust_ai]["is_ai_assisted"] is True
    assert order_map[cust_direct]["is_ai_assisted"] is False


def test_dashboard_recent_activity_endpoint():
    """9. GET /api/dashboard/activity returns recent audit logs with event types."""
    client, engine = get_test_app_client()

    with Session(engine) as session:
        audit_service.record_event(
            db=session,
            event_type="USER_REQUEST",
            action="agent_search",
            status="success",
        )
        audit_service.record_event(
            db=session,
            event_type="CART_UPDATED",
            action="add_item_to_cart",
            status="success",
        )

    res = client.get("/api/dashboard/activity?limit=10")
    assert res.status_code == 200
    data = res.json()

    assert data["total"] == 2
    assert len(data["items"]) == 2
    event_types = [item["event_type"] for item in data["items"]]
    assert "CART_UPDATED" in event_types
    assert "USER_REQUEST" in event_types


def test_dashboard_activity_limit():
    """10. GET /api/dashboard/activity?limit=1 respects limit parameter."""
    client, engine = get_test_app_client()

    with Session(engine) as session:
        for i in range(5):
            audit_service.record_event(
                db=session,
                event_type="USER_REQUEST",
                action=f"action_{i}",
                status="success",
            )

    res = client.get("/api/dashboard/activity?limit=2")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5


def test_dashboard_secret_redaction_preserved():
    """11. Verifies dashboard endpoints do not expose internal secret keys or passwords."""
    client, engine = get_test_app_client()

    with Session(engine) as session:
        audit_service.record_event(
            db=session,
            event_type="SECURITY_VIOLATION",
            action="secret_attempt",
            payload={"api_key": "secret_key_12345", "password": "mypassword"},
            status="rejected",
        )

    res = client.get("/api/dashboard/activity")
    assert res.status_code == 200
    res_text = json.dumps(res.json())
    assert "secret_key_12345" not in res_text
    assert "mypassword" not in res_text
