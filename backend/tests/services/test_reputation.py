"""Coverage for the ML seller-reputation monitor (B1):

  - parse_seller_reputation (pure, defensive)
  - reputation_service capture + latest lookups
  - reputation_risk alert evaluator
  - connector.fetch_seller_reputation (httpx mocked)
  - refresh_for_credential orchestration (connector + token patched)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.orm import Session

from src.models.alert import AlertRule, AlertType
from src.models.marketplace import (
    Marketplace,
    MarketplaceCredential,
    MarketplaceReputationSnapshot,
)
from src.services import reputation_service
from src.services.alert_evaluation_service import _evaluate_reputation_risk
from src.services.marketplaces.mercadolibre import (
    MercadoLibreConnector,
    parse_seller_reputation,
)


pytestmark = pytest.mark.db


_SAMPLE = {
    "id": 123,
    "seller_reputation": {
        "level_id": "5_green",
        "power_seller_status": "platinum",
        "transactions": {"total": 500, "completed": 480, "canceled": 6},
        "metrics": {
            # ML reports rate as a 0–1 fraction; parse normalizes ×100.
            "sales": {"period": "60 days", "completed": 480},
            "claims": {"rate": 0.015, "value": 7},
            "cancellations": {"rate": 0.008, "value": 4},
            "delayed_handling_time": {"rate": 0.032, "value": 15},
        },
    },
}


def _ml_credential(db: Session, user) -> MarketplaceCredential:
    mp = Marketplace(name="MercadoLibre", api_base_url="https://api.mercadolibre.com")
    db.add(mp)
    db.flush()
    cred = MarketplaceCredential(
        user_id=user.id, marketplace_id=mp.id,
        access_token="STUB-A", refresh_token="STUB-R",
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred


# --------------------------------------------------------------------------- #
# parse_seller_reputation
# --------------------------------------------------------------------------- #


def test_parse_extracts_all_fields_and_normalizes_rates_to_percent():
    r = parse_seller_reputation(_SAMPLE)
    assert r["level_id"] == "5_green"
    assert r["power_seller_status"] == "platinum"
    assert r["transactions_total"] == 500
    assert r["sales_completed"] == 480
    # Rates normalized from ML's 0–1 fraction to percent.
    assert r["claims_rate"] == pytest.approx(1.5)         # 0.015 → 1.5%
    assert r["claims_value"] == 7
    assert r["cancellations_rate"] == pytest.approx(0.8)  # 0.008 → 0.8%
    assert r["delayed_handling_rate"] == pytest.approx(3.2)  # 0.032 → 3.2%
    assert r["delayed_handling_value"] == 15


def test_parse_rate_normalization_examples():
    # ML doc example: real_rate 0.0912 == 9.12%.
    out = parse_seller_reputation(
        {"seller_reputation": {"metrics": {"claims": {"rate": 0.0912, "value": 24}}}}
    )
    assert out["claims_rate"] == pytest.approx(9.12)


def test_parse_is_defensive_on_empty_payload():
    r = parse_seller_reputation({})
    assert r["level_id"] is None
    assert r["claims_rate"] is None
    # New seller: seller_reputation present but no metrics yet.
    r2 = parse_seller_reputation({"seller_reputation": {"level_id": "newbie"}})
    assert r2["level_id"] == "newbie"
    assert r2["cancellations_rate"] is None


# --------------------------------------------------------------------------- #
# reputation_service capture + lookups
# --------------------------------------------------------------------------- #


def test_capture_and_latest_lookups(db, test_admin_user):
    cred = _ml_credential(db, test_admin_user)
    reputation_service.capture_snapshot(db, cred, parse_seller_reputation(_SAMPLE))
    db.commit()

    latest = reputation_service.latest_for_credential(db, cred.id)
    assert latest is not None
    assert latest.claims_rate == 1.5
    assert latest.level_id == "5_green"

    by_user = reputation_service.latest_for_user(db, test_admin_user.id)
    assert by_user is not None and by_user.id == latest.id


def test_latest_for_credential_returns_newest(db, test_admin_user):
    cred = _ml_credential(db, test_admin_user)
    older = MarketplaceReputationSnapshot(
        credential_id=cred.id, marketplace_id=cred.marketplace_id, claims_rate=1.0,
        captured_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    newer = MarketplaceReputationSnapshot(
        credential_id=cred.id, marketplace_id=cred.marketplace_id, claims_rate=2.0,
        captured_at=datetime.now(timezone.utc),
    )
    db.add_all([older, newer])
    db.commit()
    latest = reputation_service.latest_for_credential(db, cred.id)
    assert latest.claims_rate == 2.0


# --------------------------------------------------------------------------- #
# reputation_risk evaluator
# --------------------------------------------------------------------------- #


def _rule(db, user, *, threshold):
    rule = AlertRule(
        user_id=user.id, alert_type=AlertType.REPUTATION_RISK, threshold=threshold,
        window_days=30, cooldown_minutes=720, notify_email="ops@example.com", enabled=True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def test_reputation_risk_triggers_on_worst_metric(db, test_admin_user):
    cred = _ml_credential(db, test_admin_user)
    reputation_service.capture_snapshot(db, cred, parse_seller_reputation(_SAMPLE))
    db.commit()
    # worst rate is delayed_handling 3.2%; threshold 3.0 → triggered.
    result = _evaluate_reputation_risk(db, _rule(db, test_admin_user, threshold=3.0))
    assert result.triggered is True
    assert result.payload["worst_metric"] == "delayed_handling_rate"
    assert result.payload["worst_rate"] == pytest.approx(3.2)


def test_reputation_risk_below_threshold_not_triggered(db, test_admin_user):
    cred = _ml_credential(db, test_admin_user)
    reputation_service.capture_snapshot(db, cred, parse_seller_reputation(_SAMPLE))
    db.commit()
    result = _evaluate_reputation_risk(db, _rule(db, test_admin_user, threshold=5.0))
    assert result.triggered is False


def test_reputation_risk_no_snapshot_is_no_baseline(db, test_admin_user):
    result = _evaluate_reputation_risk(db, _rule(db, test_admin_user, threshold=1.0))
    assert result.triggered is False
    assert result.payload["reason"] == "no_snapshot"


# --------------------------------------------------------------------------- #
# connector + refresh orchestration
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_connector_fetch_seller_reputation_parses_response():
    connector = MercadoLibreConnector()
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(
            raise_for_status=lambda: None, json=lambda: _SAMPLE,
        )
        out = await connector.fetch_seller_reputation("TOKEN")
    assert out["claims_rate"] == 1.5
    assert out["level_id"] == "5_green"


def test_refresh_for_credential_persists_and_returns(db, test_admin_user):
    cred = _ml_credential(db, test_admin_user)

    async def _fake_token(_db, _cid):
        return "TOKEN"

    async def _fake_reputation(_token):
        return parse_seller_reputation(_SAMPLE)

    with patch(
        "src.services.marketplace_service.marketplace_service.get_valid_access_token",
        side_effect=_fake_token,
    ), patch(
        "src.services.marketplaces.mercadolibre.MercadoLibreConnector.fetch_seller_reputation",
        side_effect=_fake_reputation,
    ):
        result = reputation_service.refresh_for_credential(db, cred.id)

    assert result.error is None
    assert result.reputation is not None
    assert result.reputation.claims_rate == 1.5
    # Snapshot persisted + surfaced on the refreshed health row.
    assert reputation_service.latest_for_credential(db, cred.id) is not None
    assert result.health is not None
    assert result.health.reputation is not None


def test_refresh_for_credential_missing_is_not_found(db):
    result = reputation_service.refresh_for_credential(db, 999999)
    assert result.error == "not_found"
