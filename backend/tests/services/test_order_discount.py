"""Discount application at order-create (FP Phase 1b) — atomic + recorded."""
import datetime

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.discount import DiscountRedemption
from src.models.inventory import InventoryItem
from src.schemas.product import ProductCreate
from src.schemas.sales_order import SalesOrderCreate
from src.services import discount_service
from src.services.order_creation import create_onsite_order

pytestmark = pytest.mark.db


def _product(db: Session, sku: str, price: float = 100.0):
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Disc {sku}", sku=sku, default_resale_price=price, cost_price=20.0
        ),
    )
    db.add(InventoryItem(product_id=product.id, quantity=100, location="default"))
    db.commit()
    return product


def test_order_create_applies_discount_and_records_redemption(db, test_admin_user):
    product = _product(db, "DISC-1", price=100.0)
    discount_service.create_code(db, code="SAVE10", kind="percentage", value=10.0)
    db.commit()

    payload = SalesOrderCreate(
        idempotency_key="disc-ok-1",
        items=[{"product_id": product.id, "quantity": 2}],  # subtotal 200
        customer_user_id=test_admin_user.id,
        discount_code="save10",  # case-insensitive
    )
    order, created = create_onsite_order(db, payload, user_id=test_admin_user.id)
    db.commit()

    assert created is True
    assert order.discount_amount == 20.0
    assert order.total_price == 180.0  # 200 - 20
    assert order.discount_code_id is not None

    redemptions = (
        db.query(DiscountRedemption)
        .filter(DiscountRedemption.sales_order_id == order.id)
        .all()
    )
    assert len(redemptions) == 1
    assert redemptions[0].amount == 20.0
    assert redemptions[0].customer_user_id == test_admin_user.id


def test_order_create_rejects_expired_code(db, test_admin_user):
    product = _product(db, "DISC-2", price=100.0)
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    discount_service.create_code(db, code="OLD", kind="percentage", value=10.0, expires_at=past)
    db.commit()

    payload = SalesOrderCreate(
        idempotency_key="disc-expired-1",
        items=[{"product_id": product.id, "quantity": 1}],
        discount_code="OLD",
    )
    with pytest.raises(HTTPException) as exc:
        create_onsite_order(db, payload, user_id=test_admin_user.id)
    assert exc.value.status_code == 422
    db.rollback()


def test_max_redemptions_enforced_across_orders(db, test_admin_user):
    product = _product(db, "DISC-3", price=100.0)
    discount_service.create_code(
        db, code="ONESHOT", kind="fixed", value=25.0, max_redemptions=1
    )
    db.commit()

    p1 = SalesOrderCreate(
        idempotency_key="oneshot-1",
        items=[{"product_id": product.id, "quantity": 1}],
        discount_code="ONESHOT",
    )
    order1, _ = create_onsite_order(db, p1, user_id=test_admin_user.id)
    db.commit()
    assert order1.discount_amount == 25.0

    # Second use of the single-use code must be refused (max_redemptions reached).
    p2 = SalesOrderCreate(
        idempotency_key="oneshot-2",
        items=[{"product_id": product.id, "quantity": 1}],
        discount_code="ONESHOT",
    )
    with pytest.raises(HTTPException) as exc:
        create_onsite_order(db, p2, user_id=test_admin_user.id)
    assert exc.value.status_code == 422
    db.rollback()


def test_no_discount_code_is_unaffected(db, test_admin_user):
    product = _product(db, "DISC-4", price=100.0)
    payload = SalesOrderCreate(
        idempotency_key="nodisc-1",
        items=[{"product_id": product.id, "quantity": 1}],
    )
    order, _ = create_onsite_order(db, payload, user_id=test_admin_user.id)
    db.commit()
    assert order.total_price == 100.0
    assert order.discount_amount == 0.0
    assert order.discount_code_id is None
