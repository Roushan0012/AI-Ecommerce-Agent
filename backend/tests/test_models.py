import uuid
import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.database import Base
from app.models import Cart, CartItem, Merchant, Order, OrderItem, Payment, Product


def test_models_importable():
    """Verify all seven models are imported properly."""
    assert Merchant is not None
    assert Product is not None
    assert Order is not None
    assert OrderItem is not None
    assert Cart is not None
    assert CartItem is not None
    assert Payment is not None


def test_merchant_model_construction():
    """Verify Merchant instance construction and fields."""
    merchant_id = uuid.uuid4()
    merchant = Merchant(
        id=merchant_id,
        name="Test Store",
        description="A test commerce store",
    )
    assert merchant.id == merchant_id
    assert merchant.name == "Test Store"
    assert merchant.description == "A test commerce store"
    assert "merchants" == Merchant.__tablename__


def test_product_model_construction():
    """Verify Product instance construction and fields."""
    merchant_id = uuid.uuid4()
    product_id = uuid.uuid4()
    product = Product(
        id=product_id,
        merchant_id=merchant_id,
        name="Premium Wireless Headphones",
        description="Noise-cancelling headphones",
        category="Electronics",
        price=Decimal("4999.00"),
        currency="INR",
        inventory=50,
        sku="SKU-HEADPHONE-001",
        attributes={"color": "black", "brand": "AudioTech"},
        is_active=True,
    )
    assert product.id == product_id
    assert product.merchant_id == merchant_id
    assert product.name == "Premium Wireless Headphones"
    assert product.price == Decimal("4999.00")
    assert product.currency == "INR"
    assert product.inventory == 50
    assert product.sku == "SKU-HEADPHONE-001"
    assert product.attributes["color"] == "black"
    assert product.is_active is True
    assert "products" == Product.__tablename__


def test_cart_model_construction():
    """Verify Cart instance construction and fields."""
    cart_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    cart = Cart(
        id=cart_id,
        customer_id=customer_id,
        status="active",
        currency="INR",
        subtotal=Decimal("2499.00"),
        discount=Decimal("0.00"),
        total=Decimal("2499.00"),
    )
    assert cart.id == cart_id
    assert cart.customer_id == customer_id
    assert cart.status == "active"
    assert cart.subtotal == Decimal("2499.00")
    assert cart.total == Decimal("2499.00")
    assert "carts" == Cart.__tablename__


def test_cart_item_model_construction():
    """Verify CartItem instance construction and fields."""
    item_id = uuid.uuid4()
    cart_id = uuid.uuid4()
    product_id = uuid.uuid4()
    item = CartItem(
        id=item_id,
        cart_id=cart_id,
        product_id=product_id,
        quantity=2,
        unit_price=Decimal("1249.50"),
        total_price=Decimal("2499.00"),
    )
    assert item.id == item_id
    assert item.cart_id == cart_id
    assert item.product_id == product_id
    assert item.quantity == 2
    assert item.unit_price == Decimal("1249.50")
    assert item.total_price == Decimal("2499.00")
    assert "cart_items" == CartItem.__tablename__


def test_order_model_construction():
    """Verify Order instance construction and fields."""
    order_id = uuid.uuid4()
    merchant_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    order = Order(
        id=order_id,
        merchant_id=merchant_id,
        customer_id=customer_id,
        status="pending_payment",
        currency="INR",
        subtotal=Decimal("4999.00"),
        discount=Decimal("0.00"),
        total=Decimal("4999.00"),
        razorpay_order_id="order_rp_123456",
    )
    assert order.id == order_id
    assert order.merchant_id == merchant_id
    assert order.customer_id == customer_id
    assert order.status == "pending_payment"
    assert order.currency == "INR"
    assert order.subtotal == Decimal("4999.00")
    assert order.total == Decimal("4999.00")
    assert order.razorpay_order_id == "order_rp_123456"
    assert "orders" == Order.__tablename__


def test_order_item_model_construction():
    """Verify OrderItem instance construction and fields."""
    item_id = uuid.uuid4()
    order_id = uuid.uuid4()
    product_id = uuid.uuid4()
    item = OrderItem(
        id=item_id,
        order_id=order_id,
        product_id=product_id,
        product_name="Pro Wireless Earbuds",
        sku="SKU-AUD-01",
        quantity=2,
        unit_price=Decimal("2499.50"),
        total_price=Decimal("4999.00"),
    )
    assert item.id == item_id
    assert item.order_id == order_id
    assert item.product_id == product_id
    assert item.product_name == "Pro Wireless Earbuds"
    assert item.sku == "SKU-AUD-01"
    assert item.quantity == 2
    assert item.unit_price == Decimal("2499.50")
    assert item.total_price == Decimal("4999.00")
    assert "order_items" == OrderItem.__tablename__


def test_payment_model_construction():
    """Verify Payment instance construction and fields."""
    payment_id = uuid.uuid4()
    order_id = uuid.uuid4()
    payment = Payment(
        id=payment_id,
        order_id=order_id,
        razorpay_order_id="order_test_999",
        amount=Decimal("4999.00"),
        currency="INR",
        status="created",
    )
    assert payment.id == payment_id
    assert payment.order_id == order_id
    assert payment.razorpay_order_id == "order_test_999"
    assert payment.amount == Decimal("4999.00")
    assert payment.currency == "INR"
    assert payment.status == "created"
    assert "payments" == Payment.__tablename__


def test_model_relationships():
    """Verify bidirectional ORM relationships are properly configured."""
    merchant = Merchant(name="Store")
    product = Product(name="Item", price=Decimal("100.00"), sku="SKU1")
    cart = Cart(customer_id=uuid.uuid4(), total=Decimal("100.00"))
    cart_item = CartItem(
        cart=cart,
        product=product,
        quantity=1,
        unit_price=Decimal("100.00"),
        total_price=Decimal("100.00"),
    )
    order = Order(merchant=merchant, customer_id=cart.customer_id, cart=cart, total=Decimal("100.00"))
    order_item = OrderItem(
        product=product,
        order=order,
        product_name=product.name,
        sku=product.sku,
        quantity=1,
        unit_price=Decimal("100.00"),
        total_price=Decimal("100.00"),
    )
    payment = Payment(
        order=order,
        razorpay_order_id="order_test_123",
        amount=Decimal("100.00"),
        status="created",
    )

    # Merchant -> Products & Orders
    merchant.products.append(product)
    merchant.orders.append(order)
    assert product in merchant.products
    assert order in merchant.orders
    assert product.merchant == merchant
    assert order.merchant == merchant

    # Cart -> CartItems
    assert cart_item in cart.items
    assert cart_item.cart == cart

    # Order -> OrderItems & Product -> OrderItems & Order -> Payments
    assert order_item in order.items
    assert order_item.order == order
    assert order_item.product == product
    assert order.cart == cart
    assert payment in order.payments
    assert payment.order == order


def test_model_table_constraints():
    """Verify check and unique constraints are declared on the SQLAlchemy tables."""
    # Product constraints
    product_constraints = {c.name for c in Product.__table__.constraints}
    assert "uq_products_merchant_sku" in product_constraints
    assert "chk_products_price_non_negative" in product_constraints
    assert "chk_products_inventory_non_negative" in product_constraints

    # Cart constraints
    cart_constraints = {c.name for c in Cart.__table__.constraints}
    assert "chk_carts_subtotal_non_negative" in cart_constraints
    assert "chk_carts_discount_non_negative" in cart_constraints
    assert "chk_carts_total_non_negative" in cart_constraints

    # CartItem constraints
    cart_item_constraints = {c.name for c in CartItem.__table__.constraints}
    assert "uq_cart_items_cart_product" in cart_item_constraints
    assert "chk_cart_items_quantity_positive" in cart_item_constraints
    assert "chk_cart_items_unit_price_non_negative" in cart_item_constraints
    assert "chk_cart_items_total_price_non_negative" in cart_item_constraints

    # Order constraints
    order_constraints = {c.name for c in Order.__table__.constraints}
    assert "chk_orders_subtotal_non_negative" in order_constraints
    assert "chk_orders_discount_non_negative" in order_constraints
    assert "chk_orders_total_non_negative" in order_constraints

    # OrderItem constraints
    order_item_constraints = {c.name for c in OrderItem.__table__.constraints}
    assert "chk_order_items_quantity_positive" in order_item_constraints
    assert "chk_order_items_unit_price_non_negative" in order_item_constraints
    assert "chk_order_items_total_price_non_negative" in order_item_constraints

    # Payment constraints
    payment_constraints = {c.name for c in Payment.__table__.constraints}
    assert "chk_payments_amount_non_negative" in payment_constraints


def test_database_constraint_rejections():
    """Verify check constraints reject negative price, negative inventory, and non-positive quantity."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        merchant = Merchant(id=uuid.uuid4(), name="Test Store")
        session.add(merchant)
        session.commit()

        # 1. Reject negative price
        with pytest.raises(IntegrityError):
            bad_product = Product(
                id=uuid.uuid4(),
                merchant_id=merchant.id,
                name="Bad Price Item",
                price=Decimal("-10.00"),
                sku="SKU-NEG-PRICE",
            )
            session.add(bad_product)
            session.commit()
        session.rollback()

        # 2. Reject negative inventory
        with pytest.raises(IntegrityError):
            bad_inv = Product(
                id=uuid.uuid4(),
                merchant_id=merchant.id,
                name="Bad Inventory Item",
                price=Decimal("100.00"),
                inventory=-5,
                sku="SKU-NEG-INV",
            )
            session.add(bad_inv)
            session.commit()
        session.rollback()

        # 3. Reject non-positive quantity (0) in OrderItem
        valid_product = Product(
            id=uuid.uuid4(),
            merchant_id=merchant.id,
            name="Valid Item",
            price=Decimal("100.00"),
            inventory=10,
            sku="SKU-VALID",
        )
        order = Order(
            id=uuid.uuid4(),
            merchant_id=merchant.id,
            customer_id=uuid.uuid4(),
            total=Decimal("100.00"),
        )
        session.add_all([valid_product, order])
        session.commit()

        with pytest.raises(IntegrityError):
            bad_item = OrderItem(
                id=uuid.uuid4(),
                order_id=order.id,
                product_id=valid_product.id,
                product_name="Valid Item",
                sku="SKU-VALID",
                quantity=0,
                unit_price=Decimal("100.00"),
                total_price=Decimal("0.00"),
            )
            session.add(bad_item)
            session.commit()
        session.rollback()
