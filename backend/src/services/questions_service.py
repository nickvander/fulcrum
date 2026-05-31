"""Buyer-question ingestion + SLA helpers.

Pulls MercadoLibre `/questions` into `marketplace_questions` so the Q&A
reports surface can show unanswered questions + response-time SLA from
the DB. Mirrors `reputation_service`: a pure DB-write `ingest_*` (easily
tested) + an async `refresh_for_credential` that bridges the connector
call with `asyncio.run`, the way the health poll/reconcile actions do.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.models.marketplace import (
    Marketplace,
    MarketplaceCredential,
    MarketplaceQuestion,
)
from src.services.marketplaces.mercadolibre import parse_ml_question


logger = logging.getLogger(__name__)


def _parse_dt(value: Any) -> Optional[datetime]:
    """Parse an ML ISO-8601 timestamp (with `Z` or an offset) to a
    timezone-aware datetime. None/garbage → None."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def ingest_questions_for_credential(
    db: Session, credential: MarketplaceCredential, raw_questions: List[Dict[str, Any]],
) -> Dict[str, int]:
    """Upsert a batch of raw ML question payloads for one credential.
    Idempotent on (credential_id, external_question_id) — re-ingesting an
    answered question flips its status/answer in place. Does NOT commit."""
    created = 0
    updated = 0
    for raw in raw_questions or []:
        parsed = parse_ml_question(raw)
        ext = parsed.get("external_question_id")
        if not ext:
            continue
        fields = dict(
            item_id=parsed["item_id"],
            buyer_id=parsed["buyer_id"],
            question_text=parsed["question_text"],
            answer_text=parsed["answer_text"],
            status=parsed["status"],
            asked_at=_parse_dt(parsed["asked_at"]),
            answered_at=_parse_dt(parsed["answered_at"]),
            raw=raw,
        )
        existing = (
            db.query(MarketplaceQuestion)
            .filter(
                MarketplaceQuestion.credential_id == credential.id,
                MarketplaceQuestion.external_question_id == ext,
            )
            .first()
        )
        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
            updated += 1
        else:
            db.add(MarketplaceQuestion(
                credential_id=credential.id,
                marketplace_id=credential.marketplace_id,
                external_question_id=ext,
                **fields,
            ))
            created += 1
    db.flush()
    return {"fetched": len(raw_questions or []), "created": created, "updated": updated}


def refresh_for_credential(db: Session, credential_id: int) -> Dict[str, Any]:
    """Fetch fresh questions from the marketplace and upsert them.
    MercadoLibre-only. Returns a summary dict; on a recoverable problem
    returns `{"error": <code>}` rather than raising (mirrors the manual
    health actions). Commits on success."""
    credential = (
        db.query(MarketplaceCredential)
        .filter(MarketplaceCredential.id == credential_id)
        .first()
    )
    if credential is None:
        return {"error": "not_found"}

    marketplace = (
        db.query(Marketplace).filter(Marketplace.id == credential.marketplace_id).first()
    )
    name = (marketplace.name if marketplace else "").lower()
    if name != "mercadolibre":
        return {"error": "unsupported"}
    if credential.needs_reauthorization:
        return {"error": "needs_reauthorization"}

    from src.services.marketplace_service import (
        ReauthorizationRequiredError,
        marketplace_service,
    )
    from src.services.marketplaces.mercadolibre import MercadoLibreConnector

    connector = marketplace_service.get_connector("MercadoLibre")
    if not isinstance(connector, MercadoLibreConnector):
        return {"error": "connector_unavailable"}

    try:
        token = asyncio.run(marketplace_service.get_valid_access_token(db, credential.id))
        raw = asyncio.run(connector.fetch_questions(token))
        summary = ingest_questions_for_credential(db, credential, raw)
        db.commit()
    except ReauthorizationRequiredError:
        return {"error": "needs_reauthorization"}
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception("Questions refresh failed for credential %d", credential_id)
        return {"error": "exception"}
    return summary


def answer_question(db: Session, question_id: int, text: str) -> Dict[str, Any]:
    """Post a seller reply to a buyer question and persist it locally.

    Resolves the local `MarketplaceQuestion` by PK, sends the answer to
    MercadoLibre via the connector, then sets `answer_text`/`answered_at`/
    `status` and commits. Defensive + idempotent:

      - empty/whitespace text          → {"error": "empty"}
      - unknown question id            → {"error": "not_found"}
      - already answered               → {"error": "already_answered"}
      - non-ML / connector unavailable → {"error": "unsupported"}
      - credential needs reauth        → {"error": "needs_reauthorization"}
      - any other failure              → rollback + {"error": "exception"}

    On success returns the refreshed `MarketplaceQuestion` under
    `{"question": <model>}`.
    """
    clean = (text or "").strip()
    if not clean:
        return {"error": "empty"}

    question = (
        db.query(MarketplaceQuestion)
        .filter(MarketplaceQuestion.id == question_id)
        .first()
    )
    if question is None:
        return {"error": "not_found"}
    if question.answered_at is not None:
        return {"error": "already_answered"}

    credential = (
        db.query(MarketplaceCredential)
        .filter(MarketplaceCredential.id == question.credential_id)
        .first()
    )
    if credential is None:
        return {"error": "not_found"}

    marketplace = (
        db.query(Marketplace).filter(Marketplace.id == credential.marketplace_id).first()
    )
    name = (marketplace.name if marketplace else "").lower()
    if name != "mercadolibre":
        return {"error": "unsupported"}
    if credential.needs_reauthorization:
        return {"error": "needs_reauthorization"}

    from src.services.marketplace_service import (
        ReauthorizationRequiredError,
        marketplace_service,
    )
    from src.services.marketplaces.mercadolibre import MercadoLibreConnector

    connector = marketplace_service.get_connector("MercadoLibre")
    if not isinstance(connector, MercadoLibreConnector):
        return {"error": "connector_unavailable"}

    try:
        token = asyncio.run(marketplace_service.get_valid_access_token(db, credential.id))
        asyncio.run(
            connector.post_answer(question.external_question_id, clean, token)
        )
        question.answer_text = clean
        question.answered_at = datetime.now(timezone.utc)
        question.status = "ANSWERED"
        db.commit()
        db.refresh(question)
    except ReauthorizationRequiredError:
        db.rollback()
        return {"error": "needs_reauthorization"}
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception("Answering question %d failed", question_id)
        return {"error": "exception"}
    return {"question": question}


def poll_all_credentials_for_questions(db: Session) -> Dict[int, Dict[str, Any]]:
    """Refresh buyer questions for every MercadoLibre credential. One bad
    credential doesn't abort the loop. Returns {credential_id: summary}."""
    rows = (
        db.query(MarketplaceCredential.id)
        .join(Marketplace, Marketplace.id == MarketplaceCredential.marketplace_id)
        .filter(Marketplace.name.ilike("mercadolibre"))
        .filter(MarketplaceCredential.needs_reauthorization.is_(False))
        .all()
    )
    out: Dict[int, Dict[str, Any]] = {}
    for (credential_id,) in rows:
        out[credential_id] = refresh_for_credential(db, credential_id)
    return out
