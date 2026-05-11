import pytest

from src.crud.crud_purchase_order import purchase_order as crud_purchase_order
from src.crud.crud_supplier_product_alias import supplier_product_alias as crud_alias
from src.models.supplier import Supplier
from src.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderItemCreate


pytestmark = pytest.mark.db


@pytest.fixture
def alias_supplier(db):
    supplier = Supplier(name="Alibaba Alias Supplier", currency="USD")
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def test_confirmed_po_item_creates_supplier_alias(db, test_product, alias_supplier):
    po_in = PurchaseOrderCreate(
        supplier_id=alias_supplier.id,
        currency="USD",
        items=[
            PurchaseOrderItemCreate(
                product_id=test_product.id,
                quantity_ordered=2,
                unit_cost=12.5,
                supplier_sku="ALI-ABC-1",
                supplier_product_name="Alibaba Widget Blue 10 Pack",
            )
        ],
    )

    crud_purchase_order.create_with_items(db=db, obj_in=po_in)

    aliases = crud_alias.get_active_by_supplier(db=db, supplier_id=alias_supplier.id)
    assert len(aliases) == 1
    assert aliases[0].product_id == test_product.id
    assert aliases[0].alias_sku == "ALI-ABC-1"
    assert aliases[0].alias_name == "Alibaba Widget Blue 10 Pack"


def test_supplier_alias_can_be_deactivated_for_undo(db, test_product, alias_supplier):
    alias = crud_alias.upsert_learned_alias(
        db,
        supplier_id=alias_supplier.id,
        product_id=test_product.id,
        alias_name="Bad Alibaba Mapping",
    )
    db.commit()

    deactivated = crud_alias.deactivate(db=db, id=alias.id)

    assert deactivated is not None
    assert deactivated.is_active is False
    assert crud_alias.get_active_by_supplier(db=db, supplier_id=alias_supplier.id) == []
