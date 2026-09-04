import uuid
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.core.seed import seed_catalog
from app.main import app


def get_test_app_client():
    """Create test client with in-memory SQLite database seeded with catalog data."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    # Seed data in test database
    with Session(engine) as session:
        seed_catalog(session)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client


def test_list_products_default():
    """Verify GET /api/products returns 200 and standard pagination list."""
    client = get_test_app_client()
    response = client.get("/api/products")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 14
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert len(data["items"]) == 10


def test_list_products_pagination():
    """Verify pagination with page and page_size parameters."""
    client = get_test_app_client()
    # Page 1 (size 5)
    resp1 = client.get("/api/products?page=1&page_size=5")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert len(data1["items"]) == 5
    assert data1["page"] == 1
    assert data1["page_size"] == 5
    assert data1["total"] == 14

    # Page 2 (size 5)
    resp2 = client.get("/api/products?page=2&page_size=5")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["items"]) == 5
    assert data2["page"] == 2

    # Page 3 (size 5, remaining 4 items)
    resp3 = client.get("/api/products?page=3&page_size=5")
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert len(data3["items"]) == 4

    # Ensure page items are disjoint
    page1_ids = {item["id"] for item in data1["items"]}
    page2_ids = {item["id"] for item in data2["items"]}
    assert page1_ids.isdisjoint(page2_ids)


def test_list_products_category_filter():
    """Verify filtering products by category (case-insensitive)."""
    client = get_test_app_client()

    # Exact case
    resp_audio = client.get("/api/products?category=Audio")
    assert resp_audio.status_code == 200
    data_audio = resp_audio.json()
    assert data_audio["total"] == 3
    for item in data_audio["items"]:
        assert item["category"] == "Audio"

    # Lower case
    resp_acc = client.get("/api/products?category=computer accessories")
    assert resp_acc.status_code == 200
    data_acc = resp_acc.json()
    assert data_acc["total"] == 4
    for item in data_acc["items"]:
        assert item["category"] == "Computer Accessories"


def test_list_products_price_filter():
    """Verify filtering by min_price and max_price."""
    client = get_test_app_client()

    # min_price only (>= 5000)
    resp_min = client.get("/api/products?min_price=5000")
    assert resp_min.status_code == 200
    data_min = resp_min.json()
    assert data_min["total"] == 2
    for item in data_min["items"]:
        assert Decimal(item["price"]) >= Decimal("5000.00")

    # min_price and max_price (5000 to 20000)
    resp_range = client.get("/api/products?min_price=5000&max_price=20000")
    assert resp_range.status_code == 200
    data_range = resp_range.json()
    assert data_range["total"] == 2
    for item in data_range["items"]:
        assert Decimal("5000.00") <= Decimal(item["price"]) <= Decimal("20000.00")

    # budget items (< 1500)
    resp_budget = client.get("/api/products?max_price=1500")
    assert resp_budget.status_code == 200
    data_budget = resp_budget.json()
    for item in data_budget["items"]:
        assert Decimal(item["price"]) <= Decimal("1500.00")


def test_list_products_invalid_price_range():
    """Verify min_price > max_price returns HTTP 400 Bad Request."""
    client = get_test_app_client()
    resp = client.get("/api/products?min_price=1000&max_price=500")
    assert resp.status_code == 400
    assert "min_price cannot be greater than max_price" in resp.json()["detail"]


def test_list_products_search():
    """Verify keyword search in product name and description."""
    client = get_test_app_client()

    # Search in name
    resp_headphones = client.get("/api/products?search=headphone")
    assert resp_headphones.status_code == 200
    data = resp_headphones.json()
    assert data["total"] >= 1
    assert any("Headphone" in item["name"] for item in data["items"])

    # Search in description
    resp_gan = client.get("/api/products?search=Gallium")
    assert resp_gan.status_code == 200
    assert resp_gan.json()["total"] >= 1

    # Nonexistent search term
    resp_none = client.get("/api/products?search=xyznonexistentterm123")
    assert resp_none.status_code == 200
    assert resp_none.json()["total"] == 0
    assert resp_none.json()["items"] == []


def test_list_products_availability():
    """Verify available=true filter."""
    client = get_test_app_client()
    resp = client.get("/api/products?available=true&page_size=20")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 14
    for item in data["items"]:
        assert item["is_active"] is True
        assert item["inventory"] > 0


def test_get_product_detail_success():
    """Verify GET /api/products/{id} returns complete product data."""
    client = get_test_app_client()
    list_resp = client.get("/api/products?page_size=1")
    first_item = list_resp.json()["items"][0]
    product_id = first_item["id"]

    detail_resp = client.get(f"/api/products/{product_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()

    assert detail["id"] == product_id
    assert detail["name"] == first_item["name"]
    assert detail["sku"] == first_item["sku"]
    assert detail["price"] == first_item["price"]
    assert detail["currency"] == "INR"
    assert detail["merchant_id"] == first_item["merchant_id"]
    assert isinstance(detail["attributes"], dict)
    assert "created_at" in detail
    assert "updated_at" in detail


def test_get_product_nonexistent_returns_404():
    """Verify querying non-existent UUID returns HTTP 404."""
    client = get_test_app_client()
    random_uuid = str(uuid.uuid4())
    resp = client.get(f"/api/products/{random_uuid}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Product not found"


def test_get_product_invalid_uuid():
    """Verify invalid UUID returns HTTP 422 Unprocessable Entity."""
    client = get_test_app_client()
    resp = client.get("/api/products/not-a-valid-uuid")
    assert resp.status_code == 422


def test_product_image_url_presence():
    """Verify GET /api/products returns image_url on items and detail endpoint."""
    client = get_test_app_client()
    list_resp = client.get("/api/products?page_size=5")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) > 0

    for item in items:
        assert "image_url" in item
        assert item["image_url"] is not None
        assert item["image_url"].startswith("https://")

    # Detail endpoint
    first_id = items[0]["id"]
    detail_resp = client.get(f"/api/products/{first_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert "image_url" in detail
    assert detail["image_url"] == items[0]["image_url"]
