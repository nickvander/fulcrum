from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_active_user
from src.crud import crud_purchase_order
from src.database import get_db
from src.models.inventory import InventoryAdjustment
from src.models.marketplace import MarketplaceCredential
from src.models.product import Product
from src.models.purchase_order import PurchaseOrder
from src.models.store_settings import StoreSettings
from src.models.supplier import Supplier
from src.models.supplier_product import SupplierProduct
from src.models.supplier_product_alias import SupplierProductAlias
from src.models.user import User
from src.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderItemCreate,
    PurchaseOrderStatus,
)
from src.services.purchase_order_service import purchase_order_service

router = APIRouter()

DEMO_SUPPLIER_NAME = "[Demo] Alibaba Supplier"
DEMO_SUPPLIER_EMAIL = "demo-alibaba-supplier@fulcrum-demo.com"
LEGACY_DEMO_SUPPLIER_EMAIL = "demo-alibaba-supplier@fulcrum.local"
DEMO_PRODUCT_SKU = "DEMO-STARTER-WIDGET"
DEMO_PRODUCT_NAME = "[Demo] Starter Widget"
DEMO_PO_NOTES = "Fulcrum demo workspace - safe to review or delete before going live."
DEMO_SUPPLIER_SKU = "ALI-DEMO-WIDGET-001"
DEMO_SUPPLIER_PRODUCT_NAME = "Alibaba Demo Starter Widget"
DEMO_RECEIVE_QUANTITY = 5
DEMO_UNIT_COST = 12.5


def _step(
    *,
    key: str,
    label: str,
    description: str,
    complete: bool,
    action_label: str,
    route: str,
    optional: bool = False,
    count: int = 0,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "description": description,
        "complete": complete,
        "optional": optional,
        "warning": not complete and not optional,
        "action_label": action_label,
        "route": route,
        "count": count,
    }


@router.get("/status")
def read_onboarding_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Return customer setup health for first-run onboarding.
    """
    user_count = db.query(func.count(User.id)).scalar() or 0
    store_settings_count = db.query(func.count(StoreSettings.id)).scalar() or 0
    configured_store_count = (
        db.query(func.count(StoreSettings.id))
        .filter(StoreSettings.store_name.isnot(None))
        .scalar()
        or 0
    )
    product_count = db.query(func.count(Product.id)).scalar() or 0
    supplier_count = db.query(func.count(Supplier.id)).scalar() or 0
    supplier_product_count = db.query(func.count(SupplierProduct.id)).scalar() or 0
    alias_count = (
        db.query(func.count(SupplierProductAlias.id))
        .filter(SupplierProductAlias.is_active.is_(True))
        .scalar()
        or 0
    )
    po_count = db.query(func.count(PurchaseOrder.id)).scalar() or 0
    inventory_movement_count = db.query(func.count(InventoryAdjustment.id)).scalar() or 0
    marketplace_credential_count = db.query(func.count(MarketplaceCredential.id)).scalar() or 0

    steps = [
        _step(
            key="profile",
            label="Admin account",
            description="At least one user can sign in and manage the workspace.",
            complete=user_count > 0,
            action_label="Manage users",
            route="/users",
            count=user_count,
        ),
        _step(
            key="store",
            label="Store settings",
            description="Name the workspace and set defaults for inventory decisions.",
            complete=store_settings_count > 0 and configured_store_count > 0,
            action_label="Open settings",
            route="/settings",
            count=store_settings_count,
        ),
        _step(
            key="products",
            label="Products",
            description="Create or import products before receiving stock.",
            complete=product_count > 0,
            action_label="Add products",
            route="/products",
            count=product_count,
        ),
        _step(
            key="suppliers",
            label="Suppliers",
            description="Add suppliers so purchase orders and supplier documents have a source.",
            complete=supplier_count > 0,
            action_label="Add suppliers",
            route="/suppliers",
            count=supplier_count,
        ),
        _step(
            key="supplier_matching",
            label="Supplier matching",
            description="Link supplier names/SKUs to Fulcrum products for faster imports.",
            complete=(supplier_product_count + alias_count) > 0,
            action_label="Review suppliers",
            route="/suppliers",
            count=supplier_product_count + alias_count,
        ),
        _step(
            key="purchase_orders",
            label="Purchase orders",
            description="Create or import a supplier PO to start the stock-in workflow.",
            complete=po_count > 0,
            action_label="Create PO",
            route="/suppliers/po",
            count=po_count,
        ),
        _step(
            key="inventory",
            label="Inventory movement",
            description="Receive a PO or adjust stock so inventory has an audit trail.",
            complete=inventory_movement_count > 0,
            action_label="Receive stock",
            route="/suppliers/po",
            count=inventory_movement_count,
        ),
        _step(
            key="marketplaces",
            label="Marketplace credentials",
            description="Optional: connect channels after internal inventory is reliable.",
            complete=marketplace_credential_count > 0,
            action_label="Connect marketplace",
            route="/marketplaces",
            optional=True,
            count=marketplace_credential_count,
        ),
    ]

    required_steps = [step for step in steps if not step["optional"]]
    completed_required = sum(1 for step in required_steps if step["complete"])
    return {
        "complete": completed_required == len(required_steps),
        "completed_required": completed_required,
        "total_required": len(required_steps),
        "steps": steps,
    }


@router.post("/demo-workspace")
def create_demo_workspace(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Create a small, repeatable demo workflow for new customer onboarding.

    The seeded records intentionally run through PO creation and receiving so
    supplier aliases, inventory movement, and onboarding status are exercised
    the same way real Alibaba imports will be.
    """
    created_resources: list[str] = []

    store_settings = db.query(StoreSettings).first()
    if not store_settings:
        store_settings = StoreSettings(
            store_name="Fulcrum Demo Workspace",
            settings={"demo_workspace": True},
        )
        db.add(store_settings)
        created_resources.append("store_settings")
    elif not store_settings.store_name:
        store_settings.store_name = "Fulcrum Demo Workspace"
        existing_settings = store_settings.settings or {}
        store_settings.settings = {**existing_settings, "demo_workspace": True}
        db.add(store_settings)
        created_resources.append("store_settings")

    supplier = (
        db.query(Supplier)
        .filter(Supplier.email.in_([DEMO_SUPPLIER_EMAIL, LEGACY_DEMO_SUPPLIER_EMAIL]))
        .first()
    )
    if not supplier:
        supplier = Supplier(
            name=DEMO_SUPPLIER_NAME,
            email=DEMO_SUPPLIER_EMAIL,
            contact_person="Demo Contact",
            currency="USD",
            website="https://www.alibaba.com",
            internal_notes="Fulcrum demo supplier for onboarding. Safe to delete before going live.",
        )
        db.add(supplier)
        created_resources.append("supplier")
    elif supplier.email == LEGACY_DEMO_SUPPLIER_EMAIL:
        supplier.email = DEMO_SUPPLIER_EMAIL
        db.add(supplier)
        created_resources.append("supplier_email")

    product = db.query(Product).filter(Product.sku == DEMO_PRODUCT_SKU).first()
    if not product:
        product = Product(
            name=DEMO_PRODUCT_NAME,
            sku=DEMO_PRODUCT_SKU,
            supplier_sku=DEMO_SUPPLIER_SKU,
            supplier=supplier,
            description="Demo product used to preview supplier matching and PO receiving.",
            default_resale_price=29.99,
            cost_price=DEMO_UNIT_COST,
            average_cost=0.0,
            brand="Fulcrum Demo",
            category="Onboarding",
        )
        db.add(product)
        created_resources.append("product")

    db.commit()
    db.refresh(supplier)
    db.refresh(product)

    purchase_order = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.notes == DEMO_PO_NOTES)
        .first()
    )
    if not purchase_order:
        po_in = PurchaseOrderCreate(
            supplier_id=supplier.id,
            status=PurchaseOrderStatus.ORDERED,
            currency="USD",
            notes=DEMO_PO_NOTES,
            items=[
                PurchaseOrderItemCreate(
                    product_id=product.id,
                    quantity_ordered=DEMO_RECEIVE_QUANTITY,
                    unit_cost=DEMO_UNIT_COST,
                    supplier_sku=DEMO_SUPPLIER_SKU,
                    supplier_product_name=DEMO_SUPPLIER_PRODUCT_NAME,
                )
            ],
        )
        purchase_order = crud_purchase_order.purchase_order.create_with_items(
            db=db,
            obj_in=po_in,
        )
        created_resources.append("purchase_order")

        po_item = purchase_order.items[0]
        purchase_order = purchase_order_service.receive_items(
            db=db,
            po_id=purchase_order.id,
            received_items=[
                {
                    "po_item_id": po_item.id,
                    "product_id": product.id,
                    "quantity": DEMO_RECEIVE_QUANTITY,
                }
            ],
            user=current_user,
        )
        created_resources.append("inventory_receipt")

    return {
        "created": bool(created_resources),
        "created_resources": created_resources,
        "supplier_id": supplier.id,
        "product_id": product.id,
        "purchase_order_id": purchase_order.id,
        "message": (
            "Demo workspace created. Review the supplier, product, purchase order, "
            "and inventory movement before importing real supplier documents."
            if created_resources
            else "Demo workspace already exists. No duplicate stock was added."
        ),
    }
