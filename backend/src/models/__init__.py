"""
This package contains all SQLAlchemy ORM models.

By importing all models into this __init__.py file, we make them available
to SQLAlchemy's declarative base when it discovers table metadata, which is
crucial for correctly establishing table relationships.
"""
from .base import Base
from .product import Product, ProductImage
from .supplier import Supplier
from .inventory import InventoryItem
from .user import User
from .marketplace import Marketplace, MarketplaceCredentials, MarketplaceListing
from .order import SalesOrder, SalesOrderItem

__all__ = [
    "Base",
    "Product",
    "ProductImage",
    "Supplier",
    "InventoryItem",
    "User",
    "Marketplace",
    "MarketplaceCredentials",
    "MarketplaceListing",
    "SalesOrder",
    "SalesOrderItem",
]