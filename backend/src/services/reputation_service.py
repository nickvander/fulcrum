"""Seller-reputation capture + lookup.

MercadoLibre exposes a `seller_reputation` block (level, power-seller
status, claims / cancellations / delayed-handling metrics) that gates a
listing's buy-box and Full eligibility. We snapshot it into
`marketplace_reputation_snapshots` so:

  - the marketplace-health page can show the current standing + a trend, and
  - the `reputation_risk` alert evaluator (Celery beat, DB-only, no
    marketplace auth) can read the latest values without a live API call.

The connector call is async; we bridge with `asyncio.run` the same way
the manual poll/reconcile actions in `marketplace_health_service` do.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from src.models.marketplace import (
    Marketplace,
    MarketplaceCredential,
    MarketplaceReputationSnapshot,
)


logger = logging.getLogger(__name__)


_REPUTATION_FIELDS = (
    "level_id", "power_seller_status",
    "transactions_total", "transactions_completed", "sales_completed",
    "claims_rate", "claims_value",
    "cancellations_rate", "cancellations_value",
    "delayed_handling_rate", "delayed_handling_value",
)


def capture_snapshot(
    db: Session, credential: MarketplaceCredential, reputation: Dict[str, Any],
) -> MarketplaceReputationSnapshot:
    """Write one snapshot row from a normalized reputation dict (the
    output of `mercadolibre.parse_seller_reputation`). Does NOT commit —
    the caller owns the transaction."""
    snapshot = MarketplaceReputationSnapshot(
        credential_id=credential.id,
        marketplace_id=credential.marketplace_id,
        raw=reputation,
        **{f: reputation.get(f) for f in _REPUTATION_FIELDS},
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def latest_for_credential(
    db: Session, credential_id: int,
) -> Optional[MarketplaceReputationSnapshot]:
    return (
        db.query(MarketplaceReputationSnapshot)
        .filter(MarketplaceReputationSnapshot.credential_id == credential_id)
        .order_by(
            MarketplaceReputationSnapshot.captured_at.desc().nullslast(),
            MarketplaceReputationSnapshot.id.desc(),
        )
        .first()
    )


def latest_for_user(
    db: Session, user_id: int,
) -> Optional[MarketplaceReputationSnapshot]:
    """Most recent snapshot across all of a user's credentials — used by
    the reputation_risk alert evaluator, which is scoped to a user."""
    return (
        db.query(MarketplaceReputationSnapshot)
        .join(
            MarketplaceCredential,
            MarketplaceCredential.id == MarketplaceReputationSnapshot.credential_id,
        )
        .filter(MarketplaceCredential.user_id == user_id)
        .order_by(
            MarketplaceReputationSnapshot.captured_at.desc().nullslast(),
            MarketplaceReputationSnapshot.id.desc(),
        )
        .first()
    )


def refresh_for_credential(db: Session, credential_id: int):
    """Fetch fresh reputation from the marketplace and persist a snapshot.
    Returns a `RefreshReputationResult`. Mirrors the manual poll/reconcile
    actions in `marketplace_health_service` (asyncio bridge, error channel,
    refreshed health row). Reputation is MercadoLibre-only today."""
    from src.schemas.marketplace_health import (
        RefreshReputationResult,
        ReputationSnapshotRead,
    )

    credential = (
        db.query(MarketplaceCredential)
        .filter(MarketplaceCredential.id == credential_id)
        .first()
    )
    if credential is None:
        return RefreshReputationResult(
            credential_id=credential_id, marketplace_name="unknown", error="not_found",
        )

    marketplace = (
        db.query(Marketplace).filter(Marketplace.id == credential.marketplace_id).first()
    )
    marketplace_name = marketplace.name if marketplace else f"#{credential.marketplace_id}"
    result = RefreshReputationResult(
        credential_id=credential_id, marketplace_name=marketplace_name,
    )

    if credential.needs_reauthorization:
        result.error = "needs_reauthorization"
        return result

    if (marketplace_name or "").lower() != "mercadolibre":
        result.error = "unsupported"
        return result

    from src.services.marketplace_service import (
        ReauthorizationRequiredError,
        marketplace_service,
    )
    from src.services.marketplaces.mercadolibre import MercadoLibreConnector

    connector = marketplace_service.get_connector("MercadoLibre")
    if not isinstance(connector, MercadoLibreConnector):
        result.error = "connector_unavailable"
        return result

    try:
        token = asyncio.run(
            marketplace_service.get_valid_access_token(db, credential.id)
        )
        reputation = asyncio.run(connector.fetch_seller_reputation(token))
        snapshot = capture_snapshot(db, credential, reputation)
        db.commit()
        db.refresh(snapshot)
    except ReauthorizationRequiredError as exc:
        result.error = "needs_reauthorization"
        logger.warning(
            "Reputation refresh: ML credential %d needs reauth: %s",
            credential.id, exc.reason,
        )
        return result
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception(
            "Reputation refresh failed for credential %d", credential.id,
        )
        result.error = "exception"
        return result

    result.reputation = ReputationSnapshotRead.model_validate(snapshot)

    from src.services import marketplace_health_service
    from datetime import datetime, timezone
    result.health = marketplace_health_service._build_credential_health(
        db, credential, datetime.now(timezone.utc),
    )
    return result
