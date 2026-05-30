"""
Marketplace catalog — the single source of truth for every marketplace
Fulcrum knows about.

Why this module exists
----------------------
Marketplace identity used to be hardcoded in ~5 places: the connector
registry in `MarketplaceService`, the frontend channels page, the
add-channel dialog, the listing-type dropdown, logo resolution. Adding
a marketplace meant editing all of them and was easy to get partially
wrong (e.g. eBay defaulting to "MercadoLibre" in the settings page).

Now there's ONE declarative list. To add a marketplace:
  1. Add a `MarketplaceDefinition` entry here.
  2. (When going `live`) implement a `BaseMarketplaceConnector` and
     reference it on the entry.
The connector registry, the `/marketplace/catalog` API, and every
frontend surface all derive from this list. Removing a marketplace is
deleting (or `status="planned"`-flagging) one entry.

Status values
-------------
  - "live"    : connector implemented + OAuth wired; fully usable.
  - "beta"    : connector exists but not GA — usable with caveats.
  - "planned" : on the roadmap, no connector yet (renders "coming soon"
                in the UI, no dead connect button).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Type

from src.services.marketplaces.amazon import AmazonConnector
from src.services.marketplaces.base import BaseMarketplaceConnector
from src.services.marketplaces.mercadolibre import MercadoLibreConnector


@dataclass(frozen=True)
class MarketplaceDefinition:
    """One marketplace Fulcrum supports (or plans to)."""

    # URL-safe slug + stable identifier used everywhere (OAuth by-name,
    # logo filename, connector registry key, frontend routing).
    key: str
    display_name: str
    # "live" | "beta" | "planned"
    status: str
    # Whether the connect flow is an OAuth handshake (vs. none yet).
    supports_oauth: bool
    # The operator's home channel gets primary treatment in the UI.
    is_primary: bool
    # ISO-3166 region this channel is recommended for (drives the
    # "Recommended for Mexico" badge). None = no regional recommendation.
    recommended_region: Optional[str]
    # Brand accent color for the channel card stripe.
    brand_color: str
    # The `OrderSource` enum value orders from this channel carry, when
    # the channel produces orders. None for planned channels.
    order_source: Optional[str]
    # Backend-only: the connector class. Never serialized to the API.
    connector: Optional[Type[BaseMarketplaceConnector]] = None

    @property
    def is_connectable(self) -> bool:
        """A channel the operator can actually connect right now."""
        return self.status in ("live", "beta") and self.supports_oauth


# The catalog, in operator-priority order (primary first). This ordering
# is preserved by the API + UI so MercadoLibre always leads.
MARKETPLACE_CATALOG: list[MarketplaceDefinition] = [
    MarketplaceDefinition(
        key="mercadolibre",
        display_name="MercadoLibre",
        status="live",
        supports_oauth=True,
        is_primary=True,
        recommended_region="MX",
        brand_color="#FFE600",
        order_source="MERCADOLIBRE",
        connector=MercadoLibreConnector,
    ),
    MarketplaceDefinition(
        key="amazon",
        display_name="Amazon",
        status="live",
        supports_oauth=True,
        is_primary=False,
        recommended_region=None,
        brand_color="#FF9900",
        order_source="AMAZON",
        connector=AmazonConnector,
    ),
    MarketplaceDefinition(
        key="ebay",
        display_name="eBay",
        status="planned",
        supports_oauth=False,
        is_primary=False,
        recommended_region=None,
        brand_color="#E53238",
        order_source=None,
        connector=None,
    ),
]


def get_catalog() -> list[MarketplaceDefinition]:
    """All known marketplaces, in priority order."""
    return list(MARKETPLACE_CATALOG)


def get_definition(key: str) -> Optional[MarketplaceDefinition]:
    """Look up a marketplace by its slug (case-insensitive)."""
    if not key:
        return None
    k = key.strip().lower()
    for entry in MARKETPLACE_CATALOG:
        if entry.key == k:
            return entry
    return None


def connector_registry() -> dict[str, Type[BaseMarketplaceConnector]]:
    """`{key: connector_class}` for every entry that ships a connector.

    `MarketplaceService` builds its strategy map from this, so a new
    connector is wired simply by attaching it to a catalog entry."""
    return {
        entry.key: entry.connector
        for entry in MARKETPLACE_CATALOG
        if entry.connector is not None
    }
