"""B5 — Buyer Q&A (ML questions) ingestion + SLA reports surface."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.marketplace import (
    Marketplace,
    MarketplaceCredential,
    MarketplaceListing,
    MarketplaceQuestion,
)
from src.models.product import Product
from src.services import questions_service
from src.services.marketplaces.mercadolibre import (
    MercadoLibreConnector,
    parse_ml_question,
)


pytestmark = pytest.mark.db


def _ml_credential(db: Session, user) -> MarketplaceCredential:
    mp = db.query(Marketplace).filter(Marketplace.name.ilike("mercadolibre")).first()
    if mp is None:
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


_Q_UNANSWERED = {
    "id": 1001, "item_id": "MLM123", "status": "UNANSWERED",
    "text": "¿Tienen envío a Monterrey?", "date_created": "2026-03-01T10:00:00.000-06:00",
    "from": {"id": 555}, "answer": None,
}
_Q_ANSWERED = {
    "id": 1002, "item_id": "MLM124", "status": "ANSWERED",
    "text": "¿Viene con garantía?", "date_created": "2026-03-01T09:00:00.000-06:00",
    "from": {"id": 556},
    "answer": {"text": "Sí, 12 meses.", "date_created": "2026-03-01T09:30:00.000-06:00"},
}


# --------------------------------------------------------------------------- #
# parse + ingest
# --------------------------------------------------------------------------- #


def test_parse_ml_question_extracts_fields():
    p = parse_ml_question(_Q_ANSWERED)
    assert p["external_question_id"] == "1002"
    assert p["item_id"] == "MLM124"
    assert p["buyer_id"] == "556"
    assert p["status"] == "ANSWERED"
    assert p["answer_text"] == "Sí, 12 meses."
    assert p["answered_at"] == "2026-03-01T09:30:00.000-06:00"


def test_ingest_creates_then_updates_idempotently(db, test_admin_user):
    cred = _ml_credential(db, test_admin_user)
    s1 = questions_service.ingest_questions_for_credential(db, cred, [_Q_UNANSWERED])
    db.commit()
    assert s1 == {"fetched": 1, "created": 1, "updated": 0}

    row = (
        db.query(MarketplaceQuestion)
        .filter(MarketplaceQuestion.credential_id == cred.id)
        .one()
    )
    assert row.answered_at is None
    assert row.asked_at is not None and row.asked_at.tzinfo is not None

    # Re-ingest the same question, now answered → updates in place.
    answered = {**_Q_UNANSWERED, "status": "ANSWERED",
                "answer": {"text": "Sí", "date_created": "2026-03-02T08:00:00.000-06:00"}}
    s2 = questions_service.ingest_questions_for_credential(db, cred, [answered])
    db.commit()
    assert s2 == {"fetched": 1, "created": 0, "updated": 1}
    assert db.query(MarketplaceQuestion).filter(
        MarketplaceQuestion.credential_id == cred.id).count() == 1
    db.refresh(row)
    assert row.status == "ANSWERED"
    assert row.answered_at is not None


def test_refresh_for_credential_orchestrates(db, test_admin_user):
    cred = _ml_credential(db, test_admin_user)

    async def _token(_db, _cid):
        return "TOKEN"

    async def _questions(_token, **_kw):
        return [_Q_UNANSWERED, _Q_ANSWERED]

    with patch(
        "src.services.marketplace_service.marketplace_service.get_valid_access_token",
        side_effect=_token,
    ), patch(
        "src.services.marketplaces.mercadolibre.MercadoLibreConnector.fetch_questions",
        side_effect=_questions,
    ):
        summary = questions_service.refresh_for_credential(db, cred.id)

    assert summary == {"fetched": 2, "created": 2, "updated": 0}
    assert db.query(MarketplaceQuestion).filter(
        MarketplaceQuestion.credential_id == cred.id).count() == 2


def test_refresh_missing_credential(db):
    assert questions_service.refresh_for_credential(db, 999999) == {"error": "not_found"}


# --------------------------------------------------------------------------- #
# connector
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_fetch_questions_resolves_seller_and_returns_rows():
    connector = MercadoLibreConnector()
    me_resp = AsyncMock(raise_for_status=lambda: None, json=lambda: {"id": 777})
    q_resp = AsyncMock(raise_for_status=lambda: None,
                       json=lambda: {"questions": [_Q_UNANSWERED]})
    with patch("httpx.AsyncClient.get", side_effect=[me_resp, q_resp]):
        rows = await connector.fetch_questions("TOKEN")
    assert len(rows) == 1
    assert rows[0]["id"] == 1001


# --------------------------------------------------------------------------- #
# reports endpoint + SLA
# --------------------------------------------------------------------------- #


def test_questions_report_sla_buckets(client: TestClient, db, test_admin_user, admin_headers):
    cred = _ml_credential(db, test_admin_user)
    now = datetime.now(timezone.utc)

    def _q(ext, asked_delta_h, answered=False):
        return MarketplaceQuestion(
            credential_id=cred.id, marketplace_id=cred.marketplace_id,
            external_question_id=ext, item_id="MLM1", status="ANSWERED" if answered else "UNANSWERED",
            question_text="q", asked_at=now - timedelta(hours=asked_delta_h),
            answered_at=(now - timedelta(hours=asked_delta_h) + timedelta(hours=1)) if answered else None,
        )

    db.add_all([
        _q("A", 0.5, answered=False),   # pending (within 24h)
        _q("B", 48, answered=False),    # breached (>24h open)
        _q("C", 5, answered=True),      # answered
    ])
    db.commit()

    body = client.get(
        "/api/v1/reports/questions?window_days=30", headers=admin_headers,
    ).json()
    assert body["total"] == 3
    assert body["answered_count"] == 1
    assert body["unanswered_count"] == 2
    assert body["breached_count"] == 1
    by_ext = {r["external_question_id"]: r for r in body["rows"]}
    assert by_ext["A"]["sla_status"] == "pending"
    assert by_ext["B"]["sla_status"] == "breached"
    assert by_ext["C"]["sla_status"] == "answered"
    assert by_ext["C"]["answered"] is True
    assert by_ext["C"]["hours_open"] == pytest.approx(1.0, abs=0.2)


# --------------------------------------------------------------------------- #
# answering — connector + service + endpoint
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_post_answer_stub_token_short_circuits():
    connector = MercadoLibreConnector()
    # No live HTTP — a stub token returns a deterministic payload.
    out = await connector.post_answer("1001", "Hola", "STUB-A")
    assert out["stub"] is True
    assert out["question_id"] == "1001"
    assert out["answer"]["text"] == "Hola"


def _unanswered_question(db, cred, ext="2001"):
    now = datetime.now(timezone.utc)
    q = MarketplaceQuestion(
        credential_id=cred.id, marketplace_id=cred.marketplace_id,
        external_question_id=ext, item_id="MLM9", status="UNANSWERED",
        question_text="¿Tienen envío gratis?", asked_at=now - timedelta(hours=3),
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def test_answer_question_success(client: TestClient, db, test_admin_user, admin_headers):
    cred = _ml_credential(db, test_admin_user)
    q = _unanswered_question(db, cred)

    async def _token(_db, _cid):
        return "STUB-TOKEN"

    with patch(
        "src.services.marketplace_service.marketplace_service.get_valid_access_token",
        side_effect=_token,
    ):
        resp = client.post(
            f"/api/v1/reports/questions/{q.id}/answer",
            json={"text": "Sí, envío gratis a todo México."},
            headers=admin_headers,
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answered"] is True
    assert body["sla_status"] == "answered"
    assert body["answer_text"] == "Sí, envío gratis a todo México."

    db.refresh(q)
    assert q.answered_at is not None
    assert q.status == "ANSWERED"
    assert q.answer_text == "Sí, envío gratis a todo México."


def test_answer_question_empty_text_400(client: TestClient, db, test_admin_user, admin_headers):
    cred = _ml_credential(db, test_admin_user)
    q = _unanswered_question(db, cred, ext="2002")
    resp = client.post(
        f"/api/v1/reports/questions/{q.id}/answer",
        json={"text": "   "},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_answer_question_not_found_404(client: TestClient, db, test_admin_user, admin_headers):
    resp = client.post(
        "/api/v1/reports/questions/999999/answer",
        json={"text": "Hola"},
        headers=admin_headers,
    )
    assert resp.status_code == 404


def test_answer_question_needs_reauthorization_409(
    client: TestClient, db, test_admin_user, admin_headers,
):
    cred = _ml_credential(db, test_admin_user)
    cred.needs_reauthorization = True
    db.commit()
    q = _unanswered_question(db, cred, ext="2003")

    resp = client.post(
        f"/api/v1/reports/questions/{q.id}/answer",
        json={"text": "Hola"},
        headers=admin_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "needs_reauthorization"


def test_questions_report_status_filter(client: TestClient, db, test_admin_user, admin_headers):
    cred = _ml_credential(db, test_admin_user)
    now = datetime.now(timezone.utc)
    db.add_all([
        MarketplaceQuestion(credential_id=cred.id, marketplace_id=cred.marketplace_id,
                            external_question_id="U1", asked_at=now - timedelta(hours=2)),
        MarketplaceQuestion(credential_id=cred.id, marketplace_id=cred.marketplace_id,
                            external_question_id="A1", asked_at=now - timedelta(hours=2),
                            answered_at=now - timedelta(hours=1)),
    ])
    db.commit()
    body = client.get(
        "/api/v1/reports/questions?status=unanswered", headers=admin_headers,
    ).json()
    assert body["total"] == 1
    assert body["rows"][0]["external_question_id"] == "U1"


# --------------------------------------------------------------------------- #
# item_id → product name resolution (list + single-row builder)
# --------------------------------------------------------------------------- #


def _product(db, name, sku):
    p = Product(name=name, sku=sku)
    db.add(p)
    db.flush()
    return p


def _listing(db, *, product_id, marketplace_id, external_listing_id):
    lst = MarketplaceListing(
        product_id=product_id,
        marketplace_id=marketplace_id,
        external_listing_id=external_listing_id,
        status="ACTIVE",
    )
    db.add(lst)
    db.flush()
    return lst


def test_questions_report_resolves_item_name(
    client: TestClient, db, test_admin_user, admin_headers,
):
    cred = _ml_credential(db, test_admin_user)
    now = datetime.now(timezone.utc)

    prod = _product(db, "Taladro Inalámbrico 20V", "SKU-DRILL-1")
    _listing(db, product_id=prod.id, marketplace_id=cred.marketplace_id,
             external_listing_id="MLM-RESOLVE-1")

    db.add_all([
        # Matching listing → name resolves.
        MarketplaceQuestion(
            credential_id=cred.id, marketplace_id=cred.marketplace_id,
            external_question_id="R1", item_id="MLM-RESOLVE-1", status="UNANSWERED",
            question_text="q", asked_at=now - timedelta(hours=2),
        ),
        # item_id with no listing → item_name stays NULL.
        MarketplaceQuestion(
            credential_id=cred.id, marketplace_id=cred.marketplace_id,
            external_question_id="R2", item_id="MLM-NO-LISTING", status="UNANSWERED",
            question_text="q", asked_at=now - timedelta(hours=2),
        ),
        # No item_id at all → item_name NULL.
        MarketplaceQuestion(
            credential_id=cred.id, marketplace_id=cred.marketplace_id,
            external_question_id="R3", item_id=None, status="UNANSWERED",
            question_text="q", asked_at=now - timedelta(hours=2),
        ),
    ])
    db.commit()

    body = client.get(
        "/api/v1/reports/questions?window_days=30", headers=admin_headers,
    ).json()
    by_ext = {r["external_question_id"]: r for r in body["rows"]}
    assert by_ext["R1"]["item_name"] == "Taladro Inalámbrico 20V"
    assert by_ext["R1"]["item_id"] == "MLM-RESOLVE-1"
    assert by_ext["R2"]["item_name"] is None
    assert by_ext["R3"]["item_name"] is None


def test_questions_report_no_row_duplication_with_multiple_listings(
    client: TestClient, db, test_admin_user, admin_headers,
):
    """Two listings for the same (marketplace, item_id) must not duplicate
    the single question row or inflate the total/pagination counts."""
    cred = _ml_credential(db, test_admin_user)
    now = datetime.now(timezone.utc)

    p1 = _product(db, "Producto A", "SKU-DUP-A")
    p2 = _product(db, "Producto B", "SKU-DUP-B")
    _listing(db, product_id=p1.id, marketplace_id=cred.marketplace_id,
             external_listing_id="MLM-DUP")
    _listing(db, product_id=p2.id, marketplace_id=cred.marketplace_id,
             external_listing_id="MLM-DUP")

    db.add(MarketplaceQuestion(
        credential_id=cred.id, marketplace_id=cred.marketplace_id,
        external_question_id="DUP1", item_id="MLM-DUP", status="UNANSWERED",
        question_text="q", asked_at=now - timedelta(hours=2),
    ))
    db.commit()

    body = client.get(
        "/api/v1/reports/questions?window_days=30", headers=admin_headers,
    ).json()
    assert body["total"] == 1
    dup_rows = [r for r in body["rows"] if r["external_question_id"] == "DUP1"]
    assert len(dup_rows) == 1
    # Deterministically resolves to one of the two product names.
    assert dup_rows[0]["item_name"] in {"Producto A", "Producto B"}


def test_answer_endpoint_carries_item_name(
    client: TestClient, db, test_admin_user, admin_headers,
):
    cred = _ml_credential(db, test_admin_user)
    now = datetime.now(timezone.utc)

    prod = _product(db, "Audífonos Bluetooth", "SKU-ANS-1")
    _listing(db, product_id=prod.id, marketplace_id=cred.marketplace_id,
             external_listing_id="MLM-ANS-1")
    q = MarketplaceQuestion(
        credential_id=cred.id, marketplace_id=cred.marketplace_id,
        external_question_id="ANS1", item_id="MLM-ANS-1", status="UNANSWERED",
        question_text="¿Es original?", asked_at=now - timedelta(hours=3),
    )
    db.add(q)
    db.commit()
    db.refresh(q)

    async def _token(_db, _cid):
        return "STUB-TOKEN"

    with patch(
        "src.services.marketplace_service.marketplace_service.get_valid_access_token",
        side_effect=_token,
    ):
        resp = client.post(
            f"/api/v1/reports/questions/{q.id}/answer",
            json={"text": "Sí, 100% original."},
            headers=admin_headers,
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answered"] is True
    assert body["item_name"] == "Audífonos Bluetooth"
