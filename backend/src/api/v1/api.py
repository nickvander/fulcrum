from fastapi import APIRouter

from src.api.v1.endpoints import (
    products,
    suppliers,
    users,
    marketplace,
    uploads,
    ai,
    custom_fields,
    product_templates,
    addresses,
    audit_logs,
    bulk_users,
    purchase_orders,
    stock_transfers,
    supplier_products,
    marketplace_credentials,
    webhooks,
    settings,
    expenses,
    inventory_settings,
    marketing,
    marketing_ai,
    integrations,
    onboarding,
)

api_router = APIRouter()
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(addresses.router, prefix="/addresses", tags=["addresses"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit-logs"])
api_router.include_router(bulk_users.router, prefix="/bulk-users", tags=["bulk-users"])
api_router.include_router(marketplace.router, prefix="/marketplace", tags=["marketplace"])
api_router.include_router(marketplace_credentials.router, prefix="/marketplace-credentials", tags=["marketplace-credentials"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(inventory_settings.router, prefix="/inventory-settings", tags=["inventory-settings"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(custom_fields.router, prefix="/custom-fields", tags=["custom-fields"])
api_router.include_router(product_templates.router, prefix="/product-templates", tags=["product-templates"])
api_router.include_router(purchase_orders.router, prefix="/purchase-orders", tags=["purchase-orders"])
api_router.include_router(stock_transfers.router, prefix="/stock-transfers", tags=["stock-transfers"])
api_router.include_router(supplier_products.router, prefix="/supplier-products", tags=["supplier-products"])
api_router.include_router(expenses.router, prefix="/expenses", tags=["expenses"])
api_router.include_router(marketing.router, prefix="/marketing", tags=["marketing"])
api_router.include_router(marketing_ai.router, prefix="/marketing", tags=["marketing-ai"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])

