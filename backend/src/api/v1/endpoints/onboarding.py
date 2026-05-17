from typing import Any

from fastapi import APIRouter, Depends
from src.core.errors import LocalizedHTTPException
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_active_user
from src.crud import crud_purchase_order
from src.database import get_db
from src.models.custom_field import ProductCustomField
from src.models.expense import Expense
from src.models.inventory import InventoryAdjustment, InventoryItem
from src.models.marketplace import MarketplaceCredential, MarketplaceListing
from src.models.marketing import campaign_products, event_products
from src.models.order import SalesOrderItem
from src.models.product import BundleComponent, Product, ProductImage
from src.models.product_inventory_settings import ProductInventorySettings
from src.models.product_variant import ProductVariant
from src.models.purchase_order import PurchaseOrder
from src.models.purchase_order_item import PurchaseOrderItem
from src.models.store_settings import StoreSettings
from src.models.supplier import Supplier
from src.models.supplier_document_import import SupplierDocumentImport
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

DEMO_STORE_NAME = "Fulcrum Demo Workspace"
DEMO_SUPPLIER_NAME = "[Demo] Alibaba Supplier"
DEMO_SUPPLIER_EMAIL = "demo-alibaba-supplier@fulcrum-demo.com"
LEGACY_DEMO_SUPPLIER_EMAIL = "demo-alibaba-supplier@fulcrum.local"
DEMO_PRODUCT_SKU = "DEMO-STARTER-WIDGET"
DEMO_PRODUCT_NAME = "[Demo] Starter Widget"
# Stable picsum.photos seed so the image is deterministic for the same SKU.
DEMO_PRODUCT_IMAGE = "https://picsum.photos/seed/demo-starter-widget/640/480"
DEMO_PO_NOTES = "Fulcrum demo workspace - safe to review or delete before going live."
DEMO_SUPPLIER_SKU = "ALI-DEMO-WIDGET-001"
DEMO_SUPPLIER_PRODUCT_NAME = "Alibaba Demo Starter Widget"
DEMO_RECEIVE_QUANTITY = 5
DEMO_UNIT_COST = 12.5

# Extra demo catalog products so the list isn't sparse after demo workspace
# creation. Each entry seeds product + inventory + image, but does NOT create
# a PO so we don't muddy the "Stock In" demo. Cleanup uses the SKU prefix.
EXTRA_DEMO_CATALOG_PREFIX = "DEMO-CATALOG-"
EXTRA_DEMO_CATALOG: list[dict[str, Any]] = [
    {
        "sku": "DEMO-CATALOG-CERAMIC-MUG",
        "name": "[Demo] Ceramic Coffee Mug",
        "description": "Hand-painted Talavera ceramic mug, 350 ml. Demo product for catalog presentation.",
        "brand": "Fulcrum Demo",
        "category": "Houseware",
        "cost_price": 45.0,
        "default_resale_price": 159.0,
        "image_url": "https://picsum.photos/seed/demo-ceramic-mug/640/480",
        "initial_stock": 24,
    },
    {
        "sku": "DEMO-CATALOG-LEATHER-WALLET",
        "name": "[Demo] Bifold Leather Wallet",
        "description": "Full-grain leather bifold wallet with RFID lining. Demo product for catalog presentation.",
        "brand": "Fulcrum Demo",
        "category": "Accessories",
        "cost_price": 180.0,
        "default_resale_price": 549.0,
        "image_url": "https://picsum.photos/seed/demo-leather-wallet/640/480",
        "initial_stock": 12,
    },
    {
        "sku": "DEMO-CATALOG-BLUETOOTH-SPEAKER",
        "name": "[Demo] Portable Bluetooth Speaker",
        "description": "5W portable speaker with USB-C charging. Demo product for catalog presentation.",
        "brand": "Fulcrum Demo",
        "category": "Electronics",
        "cost_price": 320.0,
        "default_resale_price": 899.0,
        "image_url": "https://picsum.photos/seed/demo-bt-speaker/640/480",
        "initial_stock": 8,
    },
]


class DemoCleanupRequest(BaseModel):
    confirm: bool = False


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
    # The label/description/action_label strings are kept for backwards
    # compatibility (older clients still render them as-is), but the canonical
    # source for the new frontend is the *_key fields, which the Angular app
    # resolves through Transloco. Keeping the keys derived from `key` means the
    # backend doesn't need to know the user's locale.
    return {
        "key": key,
        "label": label,
        "label_key": f"onboarding.steps.{key}.label",
        "description": description,
        "description_key": f"onboarding.steps.{key}.description",
        "complete": complete,
        "optional": optional,
        "warning": not complete and not optional,
        "action_label": action_label,
        "action_label_key": f"onboarding.steps.{key}.action",
        "route": route,
        "count": count,
    }


def _count(db: Session, model: Any, *criteria: Any) -> int:
    query = db.query(func.count(model.id))
    if criteria:
        query = query.filter(*criteria)
    return query.scalar() or 0


def _table_count(db: Session, table: Any, *criteria: Any) -> int:
    query = db.query(func.count()).select_from(table)
    if criteria:
        query = query.filter(*criteria)
    return query.scalar() or 0


def _demo_record(
    *,
    key: str,
    record_type: str,
    label: str,
    description: str,
    record_id: int | None = None,
    identifier: str | None = None,
    route: str | None = None,
    safe_to_delete: bool = True,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "type": record_type,
        "id": record_id,
        "label": label,
        "identifier": identifier,
        "description": description,
        "route": route,
        "safe_to_delete": safe_to_delete,
        "blockers": blockers or [],
    }


def _get_demo_store_settings(db: Session) -> list[StoreSettings]:
    store_settings = db.query(StoreSettings).all()
    return [
        settings
        for settings in store_settings
        if settings.store_name == DEMO_STORE_NAME
        or bool((settings.settings or {}).get("demo_workspace"))
    ]


def _get_demo_supplier(db: Session) -> Supplier | None:
    return (
        db.query(Supplier)
        .filter(
            (Supplier.email.in_([DEMO_SUPPLIER_EMAIL, LEGACY_DEMO_SUPPLIER_EMAIL]))
            | (Supplier.name == DEMO_SUPPLIER_NAME)
        )
        .first()
    )


def _get_demo_product(db: Session) -> Product | None:
    return db.query(Product).filter(Product.sku == DEMO_PRODUCT_SKU).first()


def _get_demo_purchase_order(db: Session) -> PurchaseOrder | None:
    return db.query(PurchaseOrder).filter(PurchaseOrder.notes == DEMO_PO_NOTES).first()


def _is_demo_alias(alias: SupplierProductAlias) -> bool:
    return alias.alias_sku == DEMO_SUPPLIER_SKU or alias.alias_name == DEMO_SUPPLIER_PRODUCT_NAME


def _is_demo_supplier_product(supplier_product: SupplierProduct) -> bool:
    return (
        supplier_product.supplier_product_name == DEMO_SUPPLIER_PRODUCT_NAME
        or supplier_product.supplier_sku == DEMO_SUPPLIER_SKU
    )


def _demo_context(db: Session) -> dict[str, Any]:
    supplier = _get_demo_supplier(db)
    product = _get_demo_product(db)
    purchase_order = _get_demo_purchase_order(db)

    aliases: list[SupplierProductAlias] = []
    all_aliases: list[SupplierProductAlias] = []
    supplier_products: list[SupplierProduct] = []
    all_supplier_products: list[SupplierProduct] = []
    if supplier and product:
        all_aliases = (
            db.query(SupplierProductAlias)
            .filter(
                SupplierProductAlias.supplier_id == supplier.id,
                SupplierProductAlias.product_id == product.id,
            )
            .all()
        )
        aliases = [alias for alias in all_aliases if _is_demo_alias(alias)]
        all_supplier_products = (
            db.query(SupplierProduct)
            .filter(
                SupplierProduct.supplier_id == supplier.id,
                SupplierProduct.product_id == product.id,
            )
            .all()
        )
        supplier_products = [
            supplier_product
            for supplier_product in all_supplier_products
            if _is_demo_supplier_product(supplier_product)
        ]

    return {
        "store_settings": _get_demo_store_settings(db),
        "supplier": supplier,
        "product": product,
        "purchase_order": purchase_order,
        "aliases": aliases,
        "all_aliases": all_aliases,
        "supplier_products": supplier_products,
        "all_supplier_products": all_supplier_products,
    }


def _demo_product_blockers(
    db: Session,
    *,
    product: Product | None,
    supplier: Supplier | None,
    purchase_order: PurchaseOrder | None,
) -> list[str]:
    if not product:
        return []

    blockers: list[str] = []
    demo_supplier_id = supplier.id if supplier else None
    demo_po_id = purchase_order.id if purchase_order else None

    if product.supplier_id and product.supplier_id != demo_supplier_id:
        blockers.append("Demo product is assigned to a non-demo supplier.")

    po_item_query = db.query(func.count(PurchaseOrderItem.id)).filter(
        PurchaseOrderItem.product_id == product.id
    )
    if demo_po_id:
        po_item_query = po_item_query.filter(PurchaseOrderItem.po_id != demo_po_id)
    linked_po_items = po_item_query.scalar() or 0
    if linked_po_items:
        blockers.append("Demo product appears on non-demo purchase orders.")

    protected_links = [
        (_count(db, SalesOrderItem, SalesOrderItem.product_id == product.id), "sales orders"),
        (_count(db, MarketplaceListing, MarketplaceListing.product_id == product.id), "marketplace listings"),
        (_count(db, Expense, Expense.product_id == product.id), "expenses"),
        (
            _count(
                db,
                BundleComponent,
                (BundleComponent.bundle_id == product.id) | (BundleComponent.component_id == product.id),
            ),
            "bundles",
        ),
        (
            _table_count(db, campaign_products, campaign_products.c.product_id == product.id)
            + _table_count(db, event_products, event_products.c.product_id == product.id),
            "marketing plans",
        ),
    ]
    for count, label in protected_links:
        if count:
            blockers.append(f"Demo product is linked to {label}.")

    product_supplier_links = (
        db.query(SupplierProduct)
        .filter(SupplierProduct.product_id == product.id)
        .all()
    )
    if any(
        link.supplier_id != demo_supplier_id or not _is_demo_supplier_product(link)
        for link in product_supplier_links
    ):
        blockers.append("Demo product has supplier links outside the demo fingerprint.")

    product_aliases = (
        db.query(SupplierProductAlias)
        .filter(SupplierProductAlias.product_id == product.id)
        .all()
    )
    if any(
        alias.supplier_id != demo_supplier_id or not _is_demo_alias(alias)
        for alias in product_aliases
    ):
        blockers.append("Demo product has learned aliases outside the demo fingerprint.")

    non_demo_image_count = _count(
        db,
        ProductImage,
        (ProductImage.product_id == product.id)
        & ((ProductImage.source != "demo_workspace") | (ProductImage.source.is_(None))),
    )
    product_setup_links = [
        (non_demo_image_count, "images"),
        (_count(db, ProductVariant, ProductVariant.product_id == product.id), "variants"),
        (_count(db, ProductCustomField, ProductCustomField.product_id == product.id), "custom fields"),
        (
            _count(
                db,
                ProductInventorySettings,
                ProductInventorySettings.product_id == product.id,
            ),
            "inventory settings",
        ),
    ]
    for count, label in product_setup_links:
        if count:
            blockers.append(f"Demo product has {label} that may include customer setup.")

    expected_demo_reason = f"Received PO #{demo_po_id}" if demo_po_id else None
    adjustment_query = db.query(func.count(InventoryAdjustment.id)).filter(
        InventoryAdjustment.product_id == product.id
    )
    if expected_demo_reason:
        non_demo_adjustments = (
            adjustment_query.filter(
                or_(
                    InventoryAdjustment.reason != expected_demo_reason,
                    InventoryAdjustment.reason.is_(None),
                )
            ).scalar()
            or 0
        )
        if non_demo_adjustments:
            blockers.append("Demo product has inventory adjustments outside the demo receipt.")
    elif adjustment_query.scalar() or 0:
        blockers.append("Demo product has inventory adjustments but no matching demo PO was found.")

    stock_quantity = (
        db.query(func.sum(InventoryItem.quantity))
        .filter(InventoryItem.product_id == product.id)
        .scalar()
        or 0
    )
    if stock_quantity not in (0, DEMO_RECEIVE_QUANTITY):
        blockers.append("Demo product inventory quantity no longer matches the seeded demo quantity.")

    return blockers


def _demo_supplier_blockers(
    db: Session,
    *,
    supplier: Supplier | None,
    product: Product | None,
    purchase_order: PurchaseOrder | None,
) -> list[str]:
    if not supplier:
        return []

    blockers: list[str] = []
    demo_product_id = product.id if product else None
    demo_po_id = purchase_order.id if purchase_order else None

    product_query = db.query(func.count(Product.id)).filter(Product.supplier_id == supplier.id)
    if demo_product_id:
        product_query = product_query.filter(Product.id != demo_product_id)
    if product_query.scalar() or 0:
        blockers.append("Demo supplier is assigned to non-demo products.")

    po_query = db.query(func.count(PurchaseOrder.id)).filter(PurchaseOrder.supplier_id == supplier.id)
    if demo_po_id:
        po_query = po_query.filter(PurchaseOrder.id != demo_po_id)
    if po_query.scalar() or 0:
        blockers.append("Demo supplier is linked to non-demo purchase orders.")

    if _count(db, SupplierDocumentImport, SupplierDocumentImport.supplier_id == supplier.id):
        blockers.append("Demo supplier is linked to supplier document import reviews.")

    if _count(db, Expense, Expense.supplier_id == supplier.id):
        blockers.append("Demo supplier is linked to expenses.")

    supplier_product_query = db.query(func.count(SupplierProduct.id)).filter(
        SupplierProduct.supplier_id == supplier.id
    )
    alias_query = db.query(func.count(SupplierProductAlias.id)).filter(
        SupplierProductAlias.supplier_id == supplier.id
    )
    if demo_product_id:
        supplier_product_query = supplier_product_query.filter(
            SupplierProduct.product_id != demo_product_id
        )
        alias_query = alias_query.filter(SupplierProductAlias.product_id != demo_product_id)
    if supplier_product_query.scalar() or 0:
        blockers.append("Demo supplier has non-demo supplier-product links.")
    if alias_query.scalar() or 0:
        blockers.append("Demo supplier has non-demo learned aliases.")

    if demo_product_id:
        product_supplier_links = (
            db.query(SupplierProduct)
            .filter(
                SupplierProduct.supplier_id == supplier.id,
                SupplierProduct.product_id == demo_product_id,
            )
            .all()
        )
        if any(not _is_demo_supplier_product(link) for link in product_supplier_links):
            blockers.append("Demo supplier/product link has customer-edited supplier data.")

        product_aliases = (
            db.query(SupplierProductAlias)
            .filter(
                SupplierProductAlias.supplier_id == supplier.id,
                SupplierProductAlias.product_id == demo_product_id,
            )
            .all()
        )
        if any(not _is_demo_alias(alias) for alias in product_aliases):
            blockers.append("Demo supplier/product pair has non-demo learned aliases.")

    return blockers


def _demo_po_blockers(
    db: Session,
    *,
    purchase_order: PurchaseOrder | None,
    product: Product | None,
) -> list[str]:
    if not purchase_order:
        return []

    blockers: list[str] = []
    product_id = product.id if product else None
    if product_id and any(item.product_id != product_id for item in purchase_order.items):
        blockers.append("Demo purchase order contains non-demo products.")

    if purchase_order.invoices:
        blockers.append("Demo purchase order has attached supplier invoices.")

    if _count(db, Expense, Expense.purchase_order_id == purchase_order.id):
        blockers.append("Demo purchase order is linked to expenses.")

    return blockers


def _build_demo_data_report(db: Session) -> dict[str, Any]:
    context = _demo_context(db)
    store_settings: list[StoreSettings] = context["store_settings"]
    supplier: Supplier | None = context["supplier"]
    product: Product | None = context["product"]
    purchase_order: PurchaseOrder | None = context["purchase_order"]
    aliases: list[SupplierProductAlias] = context["aliases"]
    supplier_products: list[SupplierProduct] = context["supplier_products"]

    product_blockers = _demo_product_blockers(
        db,
        product=product,
        supplier=supplier,
        purchase_order=purchase_order,
    )
    supplier_blockers = _demo_supplier_blockers(
        db,
        supplier=supplier,
        product=product,
        purchase_order=purchase_order,
    )
    po_blockers = _demo_po_blockers(db, purchase_order=purchase_order, product=product)

    records: list[dict[str, Any]] = []
    for settings in store_settings:
        records.append(
            _demo_record(
                key=f"store_settings:{settings.id}",
                record_type="Store settings",
                record_id=settings.id,
                label=settings.store_name or "Demo workspace marker",
                identifier="demo_workspace",
                description="Demo workspace marker in store settings.",
                route="/settings",
            )
        )

    if supplier:
        records.append(
            _demo_record(
                key=f"supplier:{supplier.id}",
                record_type="Supplier",
                record_id=supplier.id,
                label=supplier.name,
                identifier=supplier.email,
                description="Seed supplier used for Alibaba onboarding walkthroughs.",
                route=f"/suppliers/id/{supplier.id}",
                safe_to_delete=not supplier_blockers,
                blockers=supplier_blockers,
            )
        )

    if product:
        records.append(
            _demo_record(
                key=f"product:{product.id}",
                record_type="Product",
                record_id=product.id,
                label=product.name,
                identifier=product.sku,
                description="Seed product used for supplier matching and receiving walkthroughs.",
                route="/products",
                safe_to_delete=not product_blockers,
                blockers=product_blockers,
            )
        )

        stock_quantity = (
            db.query(func.sum(InventoryItem.quantity))
            .filter(InventoryItem.product_id == product.id)
            .scalar()
            or 0
        )
        adjustment_count = _count(
            db,
            InventoryAdjustment,
            InventoryAdjustment.product_id == product.id,
        )
        if stock_quantity or adjustment_count:
            records.append(
                _demo_record(
                    key=f"inventory:{product.id}",
                    record_type="Inventory",
                    record_id=product.id,
                    label=f"{stock_quantity:g} units for {product.sku}",
                    identifier=f"{adjustment_count} audit entries",
                    description="Inventory created by the demo PO receiving flow.",
                    route="/products",
                    safe_to_delete=not product_blockers,
                    blockers=product_blockers,
                )
            )

    if purchase_order:
        records.append(
            _demo_record(
                key=f"purchase_order:{purchase_order.id}",
                record_type="Purchase order",
                record_id=purchase_order.id,
                label=f"PO #{purchase_order.id}",
                identifier=purchase_order.status,
                description="Demo purchase order used to exercise receiving and cost updates.",
                route="/suppliers/po",
                safe_to_delete=not po_blockers,
                blockers=po_blockers,
            )
        )

    for supplier_product in supplier_products:
        records.append(
            _demo_record(
                key=f"supplier_product:{supplier_product.id}",
                record_type="Supplier product link",
                record_id=supplier_product.id,
                label=supplier_product.supplier_product_name or DEMO_SUPPLIER_PRODUCT_NAME,
                identifier=DEMO_SUPPLIER_SKU,
                description="Demo supplier catalog link learned from the walkthrough PO.",
                route=f"/suppliers/id/{supplier.id}" if supplier else "/suppliers",
            )
        )

    for alias in aliases:
        records.append(
            _demo_record(
                key=f"supplier_alias:{alias.id}",
                record_type="Learned alias",
                record_id=alias.id,
                label=alias.alias_name or DEMO_SUPPLIER_PRODUCT_NAME,
                identifier=alias.alias_sku,
                description="Demo alias used to match Alibaba line items to the demo product.",
                route=f"/suppliers/id/{supplier.id}" if supplier else "/suppliers",
            )
        )

    blocked_reasons = sorted({*product_blockers, *supplier_blockers, *po_blockers})
    has_demo_data = bool(records)

    return {
        "has_demo_data": has_demo_data,
        "cleanup_available": has_demo_data and not blocked_reasons,
        "blocked_reasons": blocked_reasons,
        "records": records,
        "message": (
            "Demo records are ready for safe cleanup."
            if has_demo_data and not blocked_reasons
            else "Demo records need manual review before cleanup."
            if has_demo_data
            else "No demo records were detected."
        ),
    }


def _is_demo_only_store_settings(store_settings: StoreSettings) -> bool:
    settings = store_settings.settings or {}
    real_settings = {key: value for key, value in settings.items() if key != "demo_workspace"}
    return (
        store_settings.store_name == DEMO_STORE_NAME
        and not real_settings
        and store_settings.low_inventory_days_default in (None, 30)
        and store_settings.low_stock_quantity_default in (None, 10)
        and not store_settings.store_domain
        and not store_settings.smtp_password_encrypted
        and not store_settings.ai_enabled
        and store_settings.ai_provider in (None, "google")
        and not store_settings.ai_model
        and not store_settings.ai_google_api_key
        and not store_settings.ai_openai_api_key
        and not store_settings.ai_anthropic_api_key
        and not store_settings.ai_qwen_api_key
    )


def _cleanup_demo_data(db: Session) -> list[str]:
    context = _demo_context(db)
    removed_records: list[str] = []

    for store_settings in context["store_settings"]:
        if _is_demo_only_store_settings(store_settings):
            db.delete(store_settings)
            removed_records.append("store settings marker")
        else:
            settings = dict(store_settings.settings or {})
            if settings.pop("demo_workspace", None) is not None:
                store_settings.settings = settings
            if store_settings.store_name == DEMO_STORE_NAME:
                store_settings.store_name = None
            db.add(store_settings)
            removed_records.append("store settings demo marker")

    for alias in context["aliases"]:
        db.delete(alias)
        removed_records.append("learned alias")

    for supplier_product in context["supplier_products"]:
        db.delete(supplier_product)
        removed_records.append("supplier product link")

    purchase_order: PurchaseOrder | None = context["purchase_order"]
    if purchase_order:
        db.delete(purchase_order)
        removed_records.append("purchase order")

    product: Product | None = context["product"]
    if product:
        db.delete(product)
        removed_records.append("product and demo inventory")

    # Extra catalog products seeded by the demo workspace are fingerprinted by
    # their SKU prefix. Only remove ones the seeder owns; never sweep
    # arbitrary catalog rows.
    catalog_products = (
        db.query(Product)
        .filter(Product.sku.like(f"{EXTRA_DEMO_CATALOG_PREFIX}%"))
        .all()
    )
    for catalog_product in catalog_products:
        db.delete(catalog_product)
        removed_records.append(f"catalog product {catalog_product.sku}")

    supplier: Supplier | None = context["supplier"]
    if supplier:
        db.delete(supplier)
        removed_records.append("supplier")

    db.commit()
    return removed_records


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

    # Attach a primary image to the starter widget if it doesn't have one yet.
    # picsum.photos URLs render through the frontend's getImageUrl helper because
    # they start with `http`. No file storage round-trip needed for the demo.
    if not any(img.is_primary for img in (product.images or [])):
        primary_image = ProductImage(
            product_id=product.id,
            image_path=DEMO_PRODUCT_IMAGE,
            is_primary=1,
            source="demo_workspace",
            order=0,
            title=DEMO_PRODUCT_NAME,
        )
        db.add(primary_image)
        db.commit()
        created_resources.append("product_image")

    # Seed the extra catalog products so the product list isn't sparse after
    # demo workspace creation. They get inventory but no PO — the starter
    # widget is the one that exercises the receiving workflow.
    for spec in EXTRA_DEMO_CATALOG:
        existing = db.query(Product).filter(Product.sku == spec["sku"]).first()
        if existing:
            continue
        extra_product = Product(
            name=spec["name"],
            sku=spec["sku"],
            description=spec["description"],
            default_resale_price=spec["default_resale_price"],
            cost_price=spec["cost_price"],
            average_cost=0.0,
            brand=spec["brand"],
            category=spec["category"],
        )
        db.add(extra_product)
        db.flush()  # get id without full commit

        db.add(ProductImage(
            product_id=extra_product.id,
            image_path=spec["image_url"],
            is_primary=1,
            source="demo_workspace",
            order=0,
            title=spec["name"],
        ))
        db.add(InventoryItem(
            product_id=extra_product.id,
            quantity=spec["initial_stock"],
            location="default",
        ))
        created_resources.append(f"catalog:{spec['sku']}")

    db.commit()
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


@router.get("/demo-data")
def read_demo_data(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Return the demo records that should be reviewed before customer go-live.
    """
    return _build_demo_data_report(db)


@router.post("/demo-data/cleanup")
def cleanup_demo_data(
    *,
    request: DemoCleanupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Remove only the known Fulcrum demo records after a guarded confirmation.

    Cleanup is intentionally refused when the demo supplier/product has links
    that look like customer activity.
    """
    if not request.confirm:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.onboarding.cleanupNotConfirmed",
            detail="Demo data cleanup must be confirmed.",
        )

    report = _build_demo_data_report(db)
    if not report["has_demo_data"]:
        return {
            **report,
            "cleaned": False,
            "removed_records": [],
            "message": "No demo records were detected.",
        }

    if not report["cleanup_available"]:
        # Nested detail preserved for the dashboard component that reads
        # detail.blocked_reasons + detail.records to render the inline list.
        # The code is the canonical localization handle for the snackbar.
        raise LocalizedHTTPException(
            status_code=409,
            code="apiErrors.onboarding.cleanupBlocked",
            detail={
                "message": "Demo data cleanup was blocked to protect customer records.",
                "blocked_reasons": report["blocked_reasons"],
                "records": report["records"],
            },
        )

    removed_records = _cleanup_demo_data(db)
    refreshed_report = _build_demo_data_report(db)

    return {
        **refreshed_report,
        "cleaned": True,
        "removed_records": removed_records,
        "message": f"Demo data cleaned up by {current_user.email}.",
    }


@router.get("/launch-readiness")
def read_launch_readiness(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Summarize whether a workspace is ready for customer go-live.
    """
    status = read_onboarding_status(db)
    steps_by_key = {step["key"]: step for step in status["steps"]}

    product_count = steps_by_key["products"]["count"]
    supplier_count = steps_by_key["suppliers"]["count"]
    po_count = steps_by_key["purchase_orders"]["count"]
    inventory_movement_count = steps_by_key["inventory"]["count"]
    marketplace_count = steps_by_key["marketplaces"]["count"]
    demo_data = _build_demo_data_report(db)

    pending_import_count = (
        db.query(func.count(SupplierDocumentImport.id))
        .filter(SupplierDocumentImport.status == "pending")
        .scalar()
        or 0
    )
    demo_data_count = len(demo_data["records"])

    # Each section also emits *_key fields so the frontend can resolve copy
    # via Transloco. The description key is suffixed with the section's
    # current `status` so each state has its own translation string.
    setup_status = "ready" if status["complete"] else "blocked"
    inventory_status = "ready" if product_count and inventory_movement_count else "blocked"
    supplier_documents_status = "ready" if pending_import_count == 0 else "needs_attention"
    demo_data_status = "ready" if demo_data_count == 0 else "needs_attention"
    marketplaces_status = "optional" if marketplace_count == 0 else "ready"

    sections = [
        {
            "key": "setup",
            "label": "Setup",
            "label_key": "launchReadiness.sections.setup.label",
            "status": setup_status,
            "description": "Required onboarding steps are complete." if status["complete"] else "Required setup steps still need attention.",
            "description_key": f"launchReadiness.sections.setup.description_{setup_status}",
            "action_label": "Review checklist",
            "action_label_key": "launchReadiness.sections.setup.action",
            "route": "/dashboard",
            "metrics": {
                "completed_required": status["completed_required"],
                "total_required": status["total_required"],
            },
        },
        {
            "key": "inventory",
            "label": "Inventory",
            "label_key": "launchReadiness.sections.inventory.label",
            "status": inventory_status,
            "description": "Products and audited inventory movement exist." if product_count and inventory_movement_count else "Create products and receive or adjust stock before launch.",
            "description_key": f"launchReadiness.sections.inventory.description_{inventory_status}",
            "action_label": "Open products",
            "action_label_key": "launchReadiness.sections.inventory.action",
            "route": "/products",
            "metrics": {
                "products": product_count,
                "inventory_movements": inventory_movement_count,
            },
        },
        {
            "key": "supplier_documents",
            "label": "Supplier documents",
            "label_key": "launchReadiness.sections.supplier_documents.label",
            "status": supplier_documents_status,
            "description": "No supplier document imports are waiting for review." if pending_import_count == 0 else "Review pending supplier document imports before they become purchase orders.",
            "description_key": f"launchReadiness.sections.supplier_documents.description_{supplier_documents_status}",
            "action_label": "Open PO imports",
            "action_label_key": "launchReadiness.sections.supplier_documents.action",
            "route": "/suppliers/po",
            "metrics": {
                "pending_imports": pending_import_count,
                "purchase_orders": po_count,
                "suppliers": supplier_count,
            },
        },
        {
            "key": "demo_data",
            "label": "Demo data",
            "label_key": "launchReadiness.sections.demo_data.label",
            "status": demo_data_status,
            "description": "No demo records were detected." if demo_data_count == 0 else "Demo records exist. Review the list and clean them up before go-live.",
            "description_key": f"launchReadiness.sections.demo_data.description_{demo_data_status}",
            "action_label": "Review records",
            "action_label_key": "launchReadiness.sections.demo_data.action",
            "route": "/dashboard",
            "metrics": {
                "demo_records": demo_data_count,
            },
            "records": demo_data["records"],
            "cleanup_available": demo_data["cleanup_available"],
            "blocked_reasons": demo_data["blocked_reasons"],
        },
        {
            "key": "marketplaces",
            "label": "Marketplace connections",
            "label_key": "launchReadiness.sections.marketplaces.label",
            "status": marketplaces_status,
            "description": "Marketplace credentials are configured." if marketplace_count else "Optional for launch. Connect channels after internal inventory is reliable.",
            "description_key": f"launchReadiness.sections.marketplaces.description_{marketplaces_status}",
            "action_label": "Open marketplaces",
            "action_label_key": "launchReadiness.sections.marketplaces.action",
            "route": "/marketplaces",
            "metrics": {
                "credentials": marketplace_count,
            },
        },
    ]

    blocking = [section for section in sections if section["status"] == "blocked"]
    needs_attention = [section for section in sections if section["status"] == "needs_attention"]
    overall_status = "blocked" if blocking else "needs_attention" if needs_attention else "ready"

    return {
        "status": overall_status,
        "ready": overall_status == "ready",
        "summary": {
            "blocked": len(blocking),
            "needs_attention": len(needs_attention),
            "ready": sum(1 for section in sections if section["status"] == "ready"),
            "optional": sum(1 for section in sections if section["status"] == "optional"),
        },
        "sections": sections,
    }
