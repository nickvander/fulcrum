from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

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

router = APIRouter()


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
