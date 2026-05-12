"""
Unit tests for the MercadoLibre connector's inbound-shipment helpers.

These run as plain sync tests via asyncio.run() so they don't depend on
pytest-asyncio — which isn't always installed in pre-commit envs.
"""
import asyncio

from src.services.marketplaces.base import InboundShipmentItem
from src.services.marketplaces.mercadolibre import MercadoLibreConnector


def test_create_inbound_shipment_falls_back_to_stub_without_token():
    connector = MercadoLibreConnector()
    items = [
        InboundShipmentItem(sku="A", title="A", quantity=10),
        InboundShipmentItem(sku="B", title="B", quantity=5),
    ]
    result = asyncio.run(connector.create_inbound_shipment(items))
    assert result.external_inbound_id.startswith("ML-FULL-STUB-")
    assert result.status == "pending"
    assert result.raw_data.get("stub") is True


def test_create_inbound_shipment_with_stub_token_uses_stub():
    connector = MercadoLibreConnector()
    result = asyncio.run(
        connector.create_inbound_shipment(
            [InboundShipmentItem(sku="A", title="A", quantity=3)],
            access_token="STUB-TOKEN",
        )
    )
    assert result.external_inbound_id.startswith("ML-FULL-STUB-")


def test_get_inbound_shipment_status_stub_path():
    connector = MercadoLibreConnector()
    result = asyncio.run(
        connector.get_inbound_shipment_status("ML-FULL-STUB-1-2", access_token=None)
    )
    assert result.external_inbound_id == "ML-FULL-STUB-1-2"
    assert result.status == "pending"
