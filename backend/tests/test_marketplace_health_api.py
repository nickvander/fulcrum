"""
Tests for `/api/v1/marketplaces/health`.

Three endpoints:
  - GET / — rollup over every MarketplaceCredential
  - POST /{id}/poll-orders — synchronous wrapper around the
    per-credential ingestion entrypoint
  - POST /{id}/reconcile-inbound — synchronous wrapper around the
    per-transfer inbound reconciliation

The page itself is operator-facing; these tests prove the contracts
the frontend depends on are stable (ordering, staleness flags,
synchronous summary shape, error channel for unsupported
marketplaces / unauthorized creds).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.marketplace import (
    Marketplace,
    MarketplaceCredential,
    MarketplaceListing,
    WebhookEvent,
)
from src.models.stock_transfer import (
    LOCATION_AMAZON_FBA,
    LOCATION_INTERNAL,
    LOCATION_ML_FULL,
    StockTransfer,
    StockTransferItem,
    StockTransferStatus,
)
from src.schemas.marketplace_health import (
    INBOUND_RECONCILE_STALE_MINUTES,
    ORDER_POLL_STALE_MINUTES,
    WEBHOOK_DISCONNECT_HOURS,
)
from src.schemas.product import ProductCreate
from src.services.marketplaces.base import (
    InboundShipmentReceivedItem,
    InboundShipmentResult,
)


pytestmark = pytest.mark.db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def amazon_marketplace(db: Session) -> Marketplace:
    mp = db.query(Marketplace).filter(Marketplace.name.ilike("amazon")).first()
    if mp is None:
        mp = Marketplace(name="Amazon", api_base_url="https://sellingpartnerapi-na.amazon.com")
        db.add(mp)
        db.commit()
        db.refresh(mp)
    return mp


@pytest.fixture
def ml_marketplace(db: Session) -> Marketplace:
    mp = db.query(Marketplace).filter(Marketplace.name.ilike("mercadolibre")).first()
    if mp is None:
        mp = Marketplace(name="MercadoLibre", api_base_url="https://api.mercadolibre.com")
        db.add(mp)
        db.commit()
        db.refresh(mp)
    return mp


def _make_credential(db, marketplace, user, **overrides):
    cred = MarketplaceCredential(
        user_id=user.id,
        marketplace_id=marketplace.id,
        access_token="STUB-A",
        refresh_token="STUB-R",
    )
    for k, v in overrides.items():
        setattr(cred, k, v)
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred


# ---------------------------------------------------------------------------
# GET /marketplaces/health — list rollup
# ---------------------------------------------------------------------------


def test_list_returns_one_row_per_credential_with_staleness_flags(
    client: TestClient, db, admin_headers, test_admin_user,
    amazon_marketplace, ml_marketplace,
):
    """Two healthy credentials (one fresh, one stale) plus one reauth-
    required credential. The endpoint must return all three, ordered
    problems-first, with the right `orders_poll_stale` flags."""
    now = datetime.now(timezone.utc)

    fresh = _make_credential(
        db, amazon_marketplace, test_admin_user,
        last_orders_polled_at=now - timedelta(minutes=5),
    )
    stale = _make_credential(
        db, ml_marketplace, test_admin_user,
        last_orders_polled_at=now - timedelta(minutes=ORDER_POLL_STALE_MINUTES + 5),
    )
    reauth = _make_credential(
        db, ml_marketplace, test_admin_user,
        needs_reauthorization=True,
        last_refresh_error="invalid_grant",
    )

    response = client.get("/api/v1/marketplaces/health/", headers=admin_headers)
    assert response.status_code == 200, response.text
    body = response.json()

    # Constants exposed so the frontend can render the same numbers
    # without hardcoding.
    assert body["order_poll_stale_minutes"] == ORDER_POLL_STALE_MINUTES
    assert body["inbound_reconcile_stale_minutes"] == INBOUND_RECONCILE_STALE_MINUTES

    ids = [row["credential_id"] for row in body["items"]]
    # Reauth-required lands first (sort by needs_reauthorization desc).
    assert ids[0] == reauth.id
    # Then the stale-cursor credential before the fresh one
    # (nullsfirst + last_orders_polled_at asc).
    assert ids.index(stale.id) < ids.index(fresh.id)

    by_id = {row["credential_id"]: row for row in body["items"]}
    assert by_id[fresh.id]["orders_poll_stale"] is False
    assert by_id[stale.id]["orders_poll_stale"] is True
    assert by_id[reauth.id]["orders_poll_stale"] is True  # NULL cursor
    assert by_id[reauth.id]["needs_reauthorization"] is True
    assert by_id[reauth.id]["last_refresh_error"] == "invalid_grant"


def test_list_inbound_rollup_counts_open_and_stale_transfers(
    client: TestClient, db, admin_headers, test_admin_user,
    amazon_marketplace,
):
    """An Amazon credential with three open ml-/amazon-fba transfers:
    one fresh, one stale, one without `last_reconciled_at` yet (still
    counts as stale). open_count=3, stale_count=2."""
    cred = _make_credential(db, amazon_marketplace, test_admin_user)
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name="HEALTH-AMZN", sku="HEALTH-AMZN",
            default_resale_price=10.0, cost_price=5.0,
        ),
    )
    now = datetime.now(timezone.utc)

    def _make_transfer(*, last_reconciled_at):
        t = StockTransfer(
            source_location=LOCATION_INTERNAL,
            dest_location=LOCATION_AMAZON_FBA,
            status=StockTransferStatus.SHIPPED.value,
            external_inbound_id=f"FBA-{last_reconciled_at}",
            created_by_id=test_admin_user.id,
            last_reconciled_at=last_reconciled_at,
        )
        db.add(t)
        db.flush()
        db.add(StockTransferItem(
            transfer_id=t.id, product_id=product.id,
            qty_planned=1, qty_shipped=1, qty_received=0,
        ))
        return t

    _make_transfer(last_reconciled_at=now - timedelta(minutes=5))
    _make_transfer(
        last_reconciled_at=now - timedelta(minutes=INBOUND_RECONCILE_STALE_MINUTES + 10),
    )
    _make_transfer(last_reconciled_at=None)
    db.commit()

    response = client.get("/api/v1/marketplaces/health/", headers=admin_headers)
    body = response.json()
    row = next(r for r in body["items"] if r["credential_id"] == cred.id)
    assert row["inbound_open_count"] == 3
    # Stale = never + stale. Fresh shouldn't count.
    assert row["inbound_stale_count"] == 2


def test_list_skips_received_and_cancelled_transfers(
    client: TestClient, db, admin_headers, test_admin_user,
    amazon_marketplace,
):
    """A RECEIVED / CANCELLED / DRAFT transfer must NOT count toward
    `inbound_open_count` — the reconciler skips them, so the health
    rollup should too."""
    cred = _make_credential(db, amazon_marketplace, test_admin_user)
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name="HEALTH-CLOSED", sku="HEALTH-CLOSED",
            default_resale_price=10.0, cost_price=5.0,
        ),
    )
    for status in (
        StockTransferStatus.RECEIVED.value,
        StockTransferStatus.CANCELLED.value,
        StockTransferStatus.DRAFT.value,
    ):
        t = StockTransfer(
            source_location=LOCATION_INTERNAL,
            dest_location=LOCATION_AMAZON_FBA,
            status=status,
            external_inbound_id=f"FBA-{status}",
            created_by_id=test_admin_user.id,
        )
        db.add(t)
        db.flush()
        db.add(StockTransferItem(
            transfer_id=t.id, product_id=product.id,
            qty_planned=1, qty_shipped=1, qty_received=0,
        ))
    db.commit()

    response = client.get("/api/v1/marketplaces/health/", headers=admin_headers)
    row = next(
        r for r in response.json()["items"] if r["credential_id"] == cred.id
    )
    assert row["inbound_open_count"] == 0
    assert row["inbound_stale_count"] == 0


def test_list_requires_auth(client: TestClient):
    response = client.get("/api/v1/marketplaces/health/")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Webhook freshness signals (covers the ML "is the subscription still
# delivering?" health check requested in MISSING_ITEMS.md).
# ---------------------------------------------------------------------------


def _make_webhook(db, marketplace, *, received_at, topic="orders"):
    """Insert a WebhookEvent at a specific timestamp. The model uses
    server_default=func.now() for `received_at`, so we have to
    explicitly assign it after creation to land in the past."""
    event = WebhookEvent(
        marketplace_id=marketplace.id,
        topic=topic,
        external_resource_id=f"/{topic}/{int(received_at.timestamp())}",
        payload={"sent": received_at.isoformat()},
    )
    db.add(event)
    db.flush()
    event.received_at = received_at
    db.commit()
    db.refresh(event)
    return event


def test_list_webhook_count_reflects_last_24h_only(
    client: TestClient, db, admin_headers, test_admin_user, ml_marketplace,
):
    """3 events within 24h, 2 events older than 24h. The rollup shows
    `webhooks_received_last_24h == 3` — only the recent window
    counts. The last_received timestamp reflects the most-recent
    event regardless of window."""
    cred = _make_credential(db, ml_marketplace, test_admin_user)
    now = datetime.now(timezone.utc)

    _make_webhook(db, ml_marketplace, received_at=now - timedelta(minutes=5))
    _make_webhook(db, ml_marketplace, received_at=now - timedelta(hours=2))
    most_recent = _make_webhook(db, ml_marketplace, received_at=now - timedelta(minutes=1))
    _make_webhook(db, ml_marketplace, received_at=now - timedelta(hours=30))
    _make_webhook(db, ml_marketplace, received_at=now - timedelta(days=5))

    response = client.get("/api/v1/marketplaces/health/", headers=admin_headers)
    body = response.json()
    assert body["webhook_disconnect_hours"] == WEBHOOK_DISCONNECT_HOURS
    row = next(r for r in body["items"] if r["credential_id"] == cred.id)
    assert row["webhooks_received_last_24h"] == 3
    # `received_at` round-trips as ISO via the response model. We can't
    # use direct equality because of trailing microseconds; substring
    # is enough to confirm it's the right event.
    assert row["webhook_last_received_at"].startswith(
        most_recent.received_at.strftime("%Y-%m-%dT%H:%M"),
    )


def test_list_webhook_stats_isolated_per_marketplace(
    client: TestClient, db, admin_headers, test_admin_user,
    amazon_marketplace, ml_marketplace,
):
    """Amazon credential's webhook stats must NOT include events
    from the ML marketplace, and vice versa. WebhookEvent.marketplace_id
    is the partition key."""
    amzn_cred = _make_credential(db, amazon_marketplace, test_admin_user)
    ml_cred = _make_credential(db, ml_marketplace, test_admin_user)
    now = datetime.now(timezone.utc)

    _make_webhook(db, ml_marketplace, received_at=now - timedelta(minutes=10))
    _make_webhook(db, ml_marketplace, received_at=now - timedelta(minutes=5))
    _make_webhook(db, amazon_marketplace, received_at=now - timedelta(minutes=3))

    body = client.get(
        "/api/v1/marketplaces/health/", headers=admin_headers,
    ).json()
    by_cred = {r["credential_id"]: r for r in body["items"]}
    assert by_cred[ml_cred.id]["webhooks_received_last_24h"] == 2
    assert by_cred[amzn_cred.id]["webhooks_received_last_24h"] == 1


def test_likely_disconnected_when_credential_old_and_no_recent_webhooks(
    client: TestClient, db, admin_headers, test_admin_user, ml_marketplace,
):
    """A credential that's been around longer than the disconnect
    threshold AND has never received a webhook (or only old ones)
    should flag `webhook_likely_disconnected=True`. Catches both
    "subscription never configured" and "subscription died" cases
    via one signal."""
    cred = _make_credential(db, ml_marketplace, test_admin_user)
    # Force the credential to look old by rewriting created_at.
    cred.created_at = datetime.now(timezone.utc) - timedelta(
        hours=WEBHOOK_DISCONNECT_HOURS + 5,
    )
    db.commit()

    # No webhooks at all → likely disconnected.
    body = client.get(
        "/api/v1/marketplaces/health/", headers=admin_headers,
    ).json()
    row = next(r for r in body["items"] if r["credential_id"] == cred.id)
    assert row["webhook_likely_disconnected"] is True
    assert row["webhooks_received_last_24h"] == 0
    assert row["webhook_last_received_at"] is None

    # Add an OLD webhook (older than the disconnect threshold) — still
    # flagged disconnected because the freshness window is empty.
    _make_webhook(
        db, ml_marketplace,
        received_at=datetime.now(timezone.utc) - timedelta(
            hours=WEBHOOK_DISCONNECT_HOURS + 1,
        ),
    )
    body = client.get(
        "/api/v1/marketplaces/health/", headers=admin_headers,
    ).json()
    row = next(r for r in body["items"] if r["credential_id"] == cred.id)
    assert row["webhook_likely_disconnected"] is True


def test_likely_disconnected_false_for_fresh_credential_with_no_webhooks(
    client: TestClient, db, admin_headers, test_admin_user, ml_marketplace,
):
    """A credential that's just been connected hasn't had time to
    receive webhooks yet — DON'T flag as disconnected, otherwise
    every operator just-connecting their account would see a false
    alarm. The two-part guard (age + freshness) is what prevents
    this."""
    cred = _make_credential(db, ml_marketplace, test_admin_user)
    cred.created_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.commit()

    body = client.get(
        "/api/v1/marketplaces/health/", headers=admin_headers,
    ).json()
    row = next(r for r in body["items"] if r["credential_id"] == cred.id)
    assert row["webhook_likely_disconnected"] is False
    assert row["webhooks_received_last_24h"] == 0


def test_likely_disconnected_false_when_a_recent_webhook_exists(
    client: TestClient, db, admin_headers, test_admin_user, ml_marketplace,
):
    """A credential of any age with at least one webhook in the
    freshness window is clearly NOT disconnected — clears the flag."""
    cred = _make_credential(db, ml_marketplace, test_admin_user)
    cred.created_at = datetime.now(timezone.utc) - timedelta(days=30)
    _make_webhook(
        db, ml_marketplace,
        received_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    db.commit()

    body = client.get(
        "/api/v1/marketplaces/health/", headers=admin_headers,
    ).json()
    row = next(r for r in body["items"] if r["credential_id"] == cred.id)
    assert row["webhook_likely_disconnected"] is False
    assert row["webhooks_received_last_24h"] == 1


def test_webhook_stats_shared_across_credentials_for_same_marketplace(
    client: TestClient, db, admin_headers, test_admin_user, ml_marketplace,
):
    """ML webhooks are scoped to the app, not the user. Two ML
    credentials for the same marketplace see the SAME
    webhook_last_received_at and same recent count — they share the
    underlying subscription."""
    cred_a = _make_credential(db, ml_marketplace, test_admin_user)
    cred_b = _make_credential(db, ml_marketplace, test_admin_user)
    _make_webhook(
        db, ml_marketplace,
        received_at=datetime.now(timezone.utc) - timedelta(minutes=15),
    )

    body = client.get(
        "/api/v1/marketplaces/health/", headers=admin_headers,
    ).json()
    by_cred = {r["credential_id"]: r for r in body["items"]}
    assert by_cred[cred_a.id]["webhooks_received_last_24h"] == 1
    assert by_cred[cred_b.id]["webhooks_received_last_24h"] == 1
    assert by_cred[cred_a.id]["webhook_last_received_at"] == \
        by_cred[cred_b.id]["webhook_last_received_at"]


# ---------------------------------------------------------------------------
# POST /marketplaces/health/{id}/poll-orders
# ---------------------------------------------------------------------------


def test_poll_orders_for_amazon_credential_returns_summary_and_refreshed_health(
    client: TestClient, db, admin_headers, test_admin_user, amazon_marketplace,
):
    cred = _make_credential(db, amazon_marketplace, test_admin_user)

    with (
        patch(
            "src.services.marketplace_service.marketplace_service.get_valid_access_token",
            new=AsyncMock(return_value="LIVE-TOKEN"),
        ),
        patch(
            "src.services.amazon_order_ingestion.amazon_order_ingestion.ingest_for_credential",
            new=AsyncMock(return_value={
                "orders_new": 2, "orders_updated": 1,
                "orders_skipped": 0, "items_created": 4,
            }),
        ),
    ):
        response = client.post(
            f"/api/v1/marketplaces/health/{cred.id}/poll-orders",
            headers=admin_headers,
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["credential_id"] == cred.id
    assert body["marketplace_name"] == "Amazon"
    assert body["orders_new"] == 2
    assert body["orders_updated"] == 1
    assert body["items_created"] == 4
    assert body["error"] is None
    # Health row embedded so the UI doesn't need a follow-up list call.
    assert body["health"]["credential_id"] == cred.id


def test_poll_orders_for_ml_credential_uses_ml_ingestion_path(
    client: TestClient, db, admin_headers, test_admin_user, ml_marketplace,
):
    cred = _make_credential(db, ml_marketplace, test_admin_user)

    with (
        patch(
            "src.services.marketplace_service.marketplace_service.get_valid_access_token",
            new=AsyncMock(return_value="LIVE-TOKEN"),
        ),
        patch(
            "src.services.mercadolibre_order_ingestion.mercadolibre_order_ingestion.ingest_for_credential",
            new=AsyncMock(return_value={
                "orders_new": 3, "orders_updated": 0,
                "orders_skipped": 0, "items_created": 5,
            }),
        ) as mock_ml,
        # Amazon path should NOT be called for an ML credential —
        # cross-routing would be a regression.
        patch(
            "src.services.amazon_order_ingestion.amazon_order_ingestion.ingest_for_credential",
            new=AsyncMock(),
        ) as mock_amzn,
    ):
        response = client.post(
            f"/api/v1/marketplaces/health/{cred.id}/poll-orders",
            headers=admin_headers,
        )

    assert response.status_code == 200
    assert response.json()["orders_new"] == 3
    mock_ml.assert_awaited()
    mock_amzn.assert_not_awaited()


def test_poll_orders_short_circuits_when_credential_needs_reauthorization(
    client: TestClient, db, admin_headers, test_admin_user, amazon_marketplace,
):
    """The bulk Celery runner already skips reauth-required creds.
    The manual endpoint must do the same — surface the error code so
    the UI tells the operator to reconnect before retrying."""
    cred = _make_credential(
        db, amazon_marketplace, test_admin_user,
        needs_reauthorization=True,
        last_refresh_error="invalid_grant",
    )

    with patch(
        "src.services.amazon_order_ingestion.amazon_order_ingestion.ingest_for_credential",
        new=AsyncMock(),
    ) as mock_ingest:
        response = client.post(
            f"/api/v1/marketplaces/health/{cred.id}/poll-orders",
            headers=admin_headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["error"] == "needs_reauthorization"
    assert body["orders_new"] == 0
    mock_ingest.assert_not_awaited()


def test_poll_orders_returns_404_for_unknown_credential(
    client: TestClient, admin_headers,
):
    response = client.post(
        "/api/v1/marketplaces/health/9999999/poll-orders",
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_poll_orders_returns_unsupported_marketplace_for_custom_marketplace(
    client: TestClient, db, admin_headers, test_admin_user,
):
    """A custom Marketplace that isn't Amazon or MercadoLibre has no
    order-polling path. The endpoint returns 200 with an error code so
    the UI can render a clear message."""
    custom = Marketplace(name="Etsy", api_base_url="https://api.etsy.com")
    db.add(custom)
    db.commit()
    cred = _make_credential(db, custom, test_admin_user)

    response = client.post(
        f"/api/v1/marketplaces/health/{cred.id}/poll-orders",
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["error"] == "unsupported_marketplace"


# ---------------------------------------------------------------------------
# POST /marketplaces/health/{id}/reconcile-inbound
# ---------------------------------------------------------------------------


def test_reconcile_inbound_processes_only_this_credentials_open_transfers(
    client: TestClient, db, admin_headers, test_admin_user, amazon_marketplace,
    ml_marketplace,
):
    """An Amazon credential with two open Amazon FBA transfers, plus
    one unrelated ML transfer. The reconcile call must touch only the
    two Amazon transfers."""
    amzn_cred = _make_credential(db, amazon_marketplace, test_admin_user)
    # Also create an ML credential for completeness — the bulk runner
    # should ignore it when reconciling the Amazon credential.
    _make_credential(db, ml_marketplace, test_admin_user)

    a_product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name="RC-AMZN-A", sku="RC-AMZN-A",
            default_resale_price=10.0, cost_price=5.0,
        ),
    )
    b_product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name="RC-AMZN-B", sku="RC-AMZN-B",
            default_resale_price=10.0, cost_price=5.0,
        ),
    )
    ml_product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name="RC-ML-A", sku="RC-ML-A",
            default_resale_price=10.0, cost_price=5.0,
        ),
    )
    db.add(MarketplaceListing(
        product_id=ml_product.id, marketplace_id=ml_marketplace.id,
        external_listing_id="MLM-RC", sync_status="IN_SYNC",
    ))

    def _make_transfer(*, dest, external_id, product_id):
        t = StockTransfer(
            source_location=LOCATION_INTERNAL,
            dest_location=dest,
            status=StockTransferStatus.SHIPPED.value,
            external_inbound_id=external_id,
            created_by_id=test_admin_user.id,
        )
        db.add(t)
        db.flush()
        db.add(StockTransferItem(
            transfer_id=t.id, product_id=product_id,
            qty_planned=2, qty_shipped=2, qty_received=0,
        ))
        return t

    a = _make_transfer(dest=LOCATION_AMAZON_FBA, external_id="FBA-A", product_id=a_product.id)
    b = _make_transfer(dest=LOCATION_AMAZON_FBA, external_id="FBA-B", product_id=b_product.id)
    ml_t = _make_transfer(dest=LOCATION_ML_FULL, external_id="MLM-A", product_id=ml_product.id)
    db.commit()

    fake_connector = MagicMock()
    fake_connector.get_inbound_shipment_status = AsyncMock(
        side_effect=lambda external_id, access_token=None: InboundShipmentResult(
            external_inbound_id=external_id,
            status="receiving",
            received_items=[InboundShipmentReceivedItem(
                external_listing_id="RC-AMZN-A" if external_id == "FBA-A" else "RC-AMZN-B",
                sku="RC-AMZN-A" if external_id == "FBA-A" else "RC-AMZN-B",
                received_quantity=2,
            )],
        )
    )

    with (
        patch(
            "src.services.marketplace_service.marketplace_service.get_valid_access_token",
            new=AsyncMock(return_value="LIVE-TOKEN"),
        ),
        patch(
            "src.services.marketplace_service.marketplace_service.get_connector",
            return_value=fake_connector,
        ),
    ):
        response = client.post(
            f"/api/v1/marketplaces/health/{amzn_cred.id}/reconcile-inbound",
            headers=admin_headers,
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["transfers_processed"] == 2  # Only Amazon FBA, not the ML one
    assert body["transfers_updated"] == 2
    assert body["total_received_added"] == 4
    transfer_ids = {row["transfer_id"] for row in body["per_transfer"]}
    assert transfer_ids == {a.id, b.id}
    assert ml_t.id not in transfer_ids


def test_reconcile_inbound_returns_zero_when_no_open_transfers(
    client: TestClient, db, admin_headers, test_admin_user, amazon_marketplace,
):
    """A credential with no open transfers returns transfers_processed=0
    and no error. UI renders "Nothing to reconcile" without bothering
    the operator with a failure message."""
    cred = _make_credential(db, amazon_marketplace, test_admin_user)

    response = client.post(
        f"/api/v1/marketplaces/health/{cred.id}/reconcile-inbound",
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["transfers_processed"] == 0
    assert body["error"] is None


def test_reconcile_inbound_short_circuits_when_credential_needs_reauthorization(
    client: TestClient, db, admin_headers, test_admin_user, amazon_marketplace,
):
    cred = _make_credential(
        db, amazon_marketplace, test_admin_user,
        needs_reauthorization=True,
    )
    response = client.post(
        f"/api/v1/marketplaces/health/{cred.id}/reconcile-inbound",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["error"] == "needs_reauthorization"


def test_reconcile_inbound_404s_for_unknown_credential(
    client: TestClient, admin_headers,
):
    response = client.post(
        "/api/v1/marketplaces/health/9999999/reconcile-inbound",
        headers=admin_headers,
    )
    assert response.status_code == 404
