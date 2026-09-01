import uuid
from decimal import Decimal
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.core.seed import seed_catalog
from app.main import app
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.merchant import Merchant
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product


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


def get_first_product(client):
    """Helper to fetch first product from catalog."""
    resp = client.get("/api/products")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) > 0
    return items[0]


# 1. Create cart
def test_1_create_cart():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    res = client.post("/api/cart", json={"customer_id": customer_id})
    assert res.status_code == 200
    data = res.json()
    assert data["customer_id"] == customer_id
    assert data["status"] == "active"
    assert data["currency"] == "INR"
    assert float(data["subtotal"]) == 0.0
    assert float(data["total"]) == 0.0
    assert data["item_count"] == 0
    assert data["items"] == []


# 2. Retrieve cart
def test_2_retrieve_cart():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    create_res = client.post("/api/cart", json={"customer_id": customer_id})
    cart_id = create_res.json()["id"]

    get_res = client.get(f"/api/cart/{customer_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == cart_id
    assert get_res.json()["customer_id"] == customer_id


# 3. Add valid product
def test_3_add_valid_product():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    product = get_first_product(client)

    res = client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": 1},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == product["id"]
    assert data["items"][0]["quantity"] == 1


# 4 & 5 & 6. Add same product twice, verify duplicate not created, and quantity updates correctly
def test_4_5_6_add_same_product_twice_deduplication():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    product = get_first_product(client)

    # First add
    client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": 2},
    )
    # Second add
    res = client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": 3},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 1  # No duplicate row
    assert data["items"][0]["quantity"] == 5
    assert data["item_count"] == 5


# 7. Reject nonexistent product
def test_7_reject_nonexistent_product():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    fake_id = str(uuid.uuid4())

    res = client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": fake_id, "quantity": 1},
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


# 8. Reject inactive product
def test_8_reject_inactive_product():
    client, engine = get_test_app_client()
    customer_id = str(uuid.uuid4())

    with Session(engine) as session:
        prod = session.query(Product).first()
        prod.is_active = False
        session.commit()
        inactive_id = str(prod.id)

    res = client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": inactive_id, "quantity": 1},
    )
    assert res.status_code == 400
    assert "inactive" in res.json()["detail"].lower()


# 9. Reject zero quantity
def test_9_reject_zero_quantity():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    product = get_first_product(client)

    res = client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": 0},
    )
    assert res.status_code in [400, 422]


# 10. Reject negative quantity
def test_10_reject_negative_quantity():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    product = get_first_product(client)

    res = client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": -5},
    )
    assert res.status_code in [400, 422]


# 11. Reject quantity greater than inventory
def test_11_reject_quantity_greater_than_inventory():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    product = get_first_product(client)
    excess_qty = product["inventory"] + 100

    res = client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": excess_qty},
    )
    assert res.status_code == 400
    assert "exceeds available inventory" in res.json()["detail"]


# 12. Verify server-side unit price
def test_12_verify_serverside_unit_price():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    product = get_first_product(client)

    res = client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": 1},
    )
    assert res.status_code == 200
    assert float(res.json()["items"][0]["unit_price"]) == float(product["price"])


# 13 & 14. Verify cart subtotal and total
def test_13_14_verify_cart_subtotal_and_total():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    product = get_first_product(client)

    res = client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": 3},
    )
    assert res.status_code == 200
    expected_total = float(product["price"]) * 3
    assert float(res.json()["subtotal"]) == expected_total
    assert float(res.json()["total"]) == expected_total


# 15. Update cart quantity
def test_15_update_cart_quantity():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    product = get_first_product(client)

    client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": 1},
    )

    update_res = client.put(
        f"/api/cart/{customer_id}/items/{product['id']}",
        json={"quantity": 4},
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["items"][0]["quantity"] == 4
    assert float(data["subtotal"]) == float(product["price"]) * 4


# 16. Remove cart item
def test_16_remove_cart_item():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    product = get_first_product(client)

    client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": 2},
    )

    del_res = client.delete(f"/api/cart/{customer_id}/items/{product['id']}")
    assert del_res.status_code == 200
    data = del_res.json()
    assert len(data["items"]) == 0
    assert float(data["subtotal"]) == 0.0
    assert float(data["total"]) == 0.0


# 17. Reject empty cart order creation
def test_17_reject_empty_cart_order_creation():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    client.post("/api/cart", json={"customer_id": customer_id})

    res = client.post("/api/orders", json={"customer_id": customer_id})
    assert res.status_code == 400
    assert "empty cart" in res.json()["detail"].lower()


# 18 & 19 & 20 & 21. Create valid order, verify OrderItems, snapshots, and server-side total
def test_18_19_20_21_create_valid_order_and_verify_snapshots():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    product = get_first_product(client)

    client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": 2},
    )

    order_res = client.post("/api/orders", json={"customer_id": customer_id})
    assert order_res.status_code == 201
    order = order_res.json()

    assert order["status"] == "pending_payment"
    assert order["currency"] == "INR"
    expected_total = float(product["price"]) * 2
    assert float(order["subtotal"]) == expected_total
    assert float(order["total"]) == expected_total

    assert len(order["items"]) == 1
    item = order["items"][0]
    assert item["product_id"] == product["id"]
    assert item["product_name"] == product["name"]
    assert item["sku"] == product["sku"]
    assert float(item["unit_price"]) == float(product["price"])
    assert item["quantity"] == 2
    assert float(item["total_price"]) == expected_total


# 22. Attempt client price manipulation
def test_22_attempt_client_price_manipulation():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    product = get_first_product(client)

    client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": 1, "unit_price": 0.01},
    )

    cart = client.get(f"/api/cart/{customer_id}").json()
    assert float(cart["items"][0]["unit_price"]) == float(product["price"])
    assert float(cart["total"]) == float(product["price"])


# 23. Attempt client total manipulation
def test_23_attempt_client_total_manipulation():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    product = get_first_product(client)

    client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": 1},
    )

    order_res = client.post(
        "/api/orders", json={"customer_id": customer_id, "total": 1.00, "subtotal": 1.00}
    )
    assert order_res.status_code == 201
    assert float(order_res.json()["total"]) == float(product["price"])


# 24. Revalidate inventory during order creation
def test_24_revalidate_inventory_during_order_creation():
    client, engine = get_test_app_client()
    customer_id = str(uuid.uuid4())
    product = get_first_product(client)

    client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": 10},
    )

    # Drop inventory in DB before checkout
    with Session(engine) as session:
        prod = session.query(Product).filter_by(id=uuid.UUID(product["id"])).first()
        prod.inventory = 3
        session.commit()

    res = client.post("/api/orders", json={"customer_id": customer_id})
    assert res.status_code == 400
    assert "Insufficient inventory" in res.json()["detail"]


# 25. Reject duplicate conversion of finalized cart
def test_25_reject_duplicate_conversion_of_cart():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    product = get_first_product(client)

    client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": 1},
    )

    res1 = client.post("/api/orders", json={"customer_id": customer_id})
    assert res1.status_code == 201

    res2 = client.post("/api/orders", json={"customer_id": customer_id})
    assert res2.status_code == 404


# 26. Retrieve customer orders
def test_26_retrieve_customer_orders():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    product = get_first_product(client)

    client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": 1},
    )
    client.post("/api/orders", json={"customer_id": customer_id})

    res = client.get(f"/api/orders/{customer_id}")
    assert res.status_code == 200
    assert res.json()["total"] == 1


# 27. Retrieve specific order
def test_27_retrieve_specific_order():
    client, _ = get_test_app_client()
    customer_id = str(uuid.uuid4())
    product = get_first_product(client)

    client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": 1},
    )
    order_id = client.post("/api/orders", json={"customer_id": customer_id}).json()["id"]

    res = client.get(f"/api/orders/{customer_id}/{order_id}")
    assert res.status_code == 200
    assert res.json()["id"] == order_id


# 28. Reject order belonging to another customer
def test_28_reject_order_belonging_to_another_customer():
    client, _ = get_test_app_client()
    customer_a = str(uuid.uuid4())
    customer_b = str(uuid.uuid4())
    product = get_first_product(client)

    client.post(
        f"/api/cart/{customer_a}/items",
        json={"product_id": product["id"], "quantity": 1},
    )
    order_a_id = client.post("/api/orders", json={"customer_id": customer_a}).json()["id"]

    res = client.get(f"/api/orders/{customer_b}/{order_a_id}")
    assert res.status_code == 404
    assert "Order not found" in res.json()["detail"]


# 29. Verify transaction rollback on order creation failure
def test_29_transaction_rollback_on_failure():
    client, engine = get_test_app_client()
    customer_id = str(uuid.uuid4())
    product = get_first_product(client)

    client.post(
        f"/api/cart/{customer_id}/items",
        json={"product_id": product["id"], "quantity": 1},
    )

    # Force an unhandled error inside order creation commit by monkeypatching
    with patch("app.services.order_service.OrderService.format_order_response", side_effect=Exception("Simulated Failure")):
        with patch.object(Session, "commit", side_effect=Exception("Database commit error")):
            res = client.post("/api/orders", json={"customer_id": customer_id})
            assert res.status_code == 500

    # Verify no partial orders exist in DB
    with Session(engine) as session:
        orders = session.query(Order).all()
        assert len(orders) == 0
        order_items = session.query(OrderItem).all()
        assert len(order_items) == 0
