"""Coverage for the marketplace catalog — the single source of truth
for supported marketplaces.

  - services/marketplace_catalog.py  (catalog, lookup, connector registry)
  - GET /api/v1/marketplace/catalog
  - MarketplaceService derives its connector map from the catalog
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.services import marketplace_catalog
from src.services.marketplace_service import MarketplaceService


# --------------------------------------------------------------------------- #
# Catalog module
# --------------------------------------------------------------------------- #


def test_catalog_lists_known_marketplaces_primary_first():
    catalog = marketplace_catalog.get_catalog()
    keys = [d.key for d in catalog]
    assert keys[0] == "mercadolibre"  # primary leads
    assert "amazon" in keys
    assert "ebay" in keys
    # The primary flag is on MercadoLibre and nothing else.
    primaries = [d.key for d in catalog if d.is_primary]
    assert primaries == ["mercadolibre"]


def test_get_definition_is_case_insensitive():
    assert marketplace_catalog.get_definition("MercadoLibre").key == "mercadolibre"
    assert marketplace_catalog.get_definition("AMAZON").key == "amazon"
    assert marketplace_catalog.get_definition("nope") is None
    assert marketplace_catalog.get_definition("") is None


def test_is_connectable_reflects_status_and_oauth():
    ml = marketplace_catalog.get_definition("mercadolibre")
    ebay = marketplace_catalog.get_definition("ebay")
    assert ml.is_connectable is True          # live + oauth
    assert ebay.is_connectable is False        # planned, no oauth


def test_connector_registry_only_includes_entries_with_a_connector():
    reg = marketplace_catalog.connector_registry()
    assert "mercadolibre" in reg
    assert "amazon" in reg
    # eBay is planned (no connector) → excluded.
    assert "ebay" not in reg


# --------------------------------------------------------------------------- #
# Order-source helpers — the unification with the OrderSource column
# --------------------------------------------------------------------------- #


def test_order_sources_includes_internal_and_catalog_marketplaces():
    sources = marketplace_catalog.order_sources()
    # FULCRUM (internal/direct) is first, then the catalog marketplaces
    # that produce orders.
    assert sources[0] == "FULCRUM"
    assert "MERCADOLIBRE" in sources
    assert "AMAZON" in sources
    # eBay is planned with no order_source → not a valid order source yet.
    assert "EBAY" not in sources


def test_is_valid_order_source_is_case_insensitive():
    assert marketplace_catalog.is_valid_order_source("mercadolibre") is True
    assert marketplace_catalog.is_valid_order_source("AMAZON") is True
    assert marketplace_catalog.is_valid_order_source("FULCRUM") is True
    assert marketplace_catalog.is_valid_order_source("ebay") is False
    assert marketplace_catalog.is_valid_order_source("walmart") is False
    assert marketplace_catalog.is_valid_order_source("") is False


def test_source_marketplace_name_round_trips():
    assert marketplace_catalog.marketplace_name_for_source("AMAZON") == "amazon"
    assert marketplace_catalog.marketplace_name_for_source("MERCADOLIBRE") == "mercadolibre"
    # FULCRUM is not a marketplace → no name.
    assert marketplace_catalog.marketplace_name_for_source("FULCRUM") is None
    # Inverse direction.
    assert marketplace_catalog.source_for_marketplace_name("amazon") == "AMAZON"
    assert marketplace_catalog.source_for_marketplace_name("ebay") is None  # planned, no order_source


# --------------------------------------------------------------------------- #
# MarketplaceService derives from the catalog
# --------------------------------------------------------------------------- #


def test_service_connectors_come_from_catalog():
    svc = MarketplaceService()
    # The strategy map matches the catalog's connector registry.
    assert set(svc._connectors.keys()) == set(
        marketplace_catalog.connector_registry().keys()
    )
    # And resolving a live connector works; an unknown one raises.
    assert svc.get_connector("mercadolibre") is not None
    with pytest.raises(ValueError):
        svc.get_connector("ebay")  # planned → not in the registry


# --------------------------------------------------------------------------- #
# Endpoint
# --------------------------------------------------------------------------- #


@pytest.mark.db
def test_catalog_endpoint_returns_serialized_entries(client: TestClient, admin_headers):
    resp = client.get("/api/v1/marketplace/catalog", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    by_key = {r["key"]: r for r in rows}

    assert by_key["mercadolibre"]["is_primary"] is True
    assert by_key["mercadolibre"]["recommended_region"] == "MX"
    assert by_key["mercadolibre"]["is_connectable"] is True

    assert by_key["ebay"]["status"] == "planned"
    assert by_key["ebay"]["is_connectable"] is False

    # No connector class leaks into the serialized payload.
    assert "connector" not in by_key["amazon"]
    # Priority order preserved (MercadoLibre first).
    assert rows[0]["key"] == "mercadolibre"


@pytest.mark.db
def test_catalog_endpoint_requires_auth(client: TestClient):
    resp = client.get("/api/v1/marketplace/catalog")
    assert resp.status_code == 401
