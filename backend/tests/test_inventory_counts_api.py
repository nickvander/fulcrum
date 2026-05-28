"""Coverage for the physical-count session workflow.

Three layers:
  1. Lifecycle: start → add → update → commit / cancel.
  2. State machine: editing a committed/cancelled session is a 409.
  3. Commit math: every non-NULL counted row != expected writes a
     `reason_code='recount'` adjustment with the right delta;
     zero-delta and NULL-counted rows are skipped.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.inventory import (
    InventoryAdjustment,
    InventoryItem,
)
from src.schemas.product import ProductCreate


pytestmark = pytest.mark.db


_COUNTER = {"n": 0}


def _seed_product(db: Session, *, on_hand: int, sku_prefix: str = "CT") -> str:
    _COUNTER["n"] += 1
    suffix = _COUNTER["n"]
    sku = f"{sku_prefix}-{suffix}"
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Count Product {suffix}", sku=sku,
            default_resale_price=10.0, cost_price=5.0,
        ),
    )
    db.add(InventoryItem(product_id=product.id, quantity=on_hand, location="default"))
    db.commit()
    return sku


def _start_session(client: TestClient, admin_headers) -> dict:
    resp = client.post(
        "/api/v1/inventory-counts/",
        json={"location": "default", "notes": "monthly count"},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_start_session_returns_in_progress_with_zero_items(
    client: TestClient, db, admin_headers,
):
    session = _start_session(client, admin_headers)
    assert session["status"] == "in_progress"
    assert session["location"] == "default"
    assert session["notes"] == "monthly count"
    assert session["items"] == []
    # Recorder is the admin user (admin_headers fixture).
    assert session["started_by_email"] == "admin@test.com"


def test_add_item_snapshots_expected_qty_from_inventory(
    client: TestClient, db, admin_headers,
):
    """Adding a SKU records the live `InventoryItem.quantity` as
    expected — that's what the operator will be comparing their
    physical count against."""
    sku = _seed_product(db, on_hand=42)
    session = _start_session(client, admin_headers)

    resp = client.post(
        f"/api/v1/inventory-counts/{session['id']}/items",
        json={"sku": sku},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    item = resp.json()
    assert item["product_sku"] == sku
    assert item["expected_quantity"] == 42
    assert item["counted_quantity"] is None


def test_add_item_treats_missing_inventory_row_as_zero_expected(
    client: TestClient, db, admin_headers,
):
    """If the product has no InventoryItem yet (new SKU; commit will
    create one), expected is 0 — the operator's count becomes the
    initial stock level."""
    sku_new = f"NEW-{_COUNTER['n'] + 1}"
    crud_product.product.create(
        db=db,
        obj_in=ProductCreate(name="Fresh", sku=sku_new, default_resale_price=10.0, cost_price=5.0),
    )
    _COUNTER["n"] += 1
    db.commit()
    session = _start_session(client, admin_headers)

    resp = client.post(
        f"/api/v1/inventory-counts/{session['id']}/items",
        json={"sku": sku_new},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["expected_quantity"] == 0


def test_add_item_unknown_sku_returns_404(
    client: TestClient, db, admin_headers,
):
    session = _start_session(client, admin_headers)
    resp = client.post(
        f"/api/v1/inventory-counts/{session['id']}/items",
        json={"sku": "DOES-NOT-EXIST"},
        headers=admin_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "apiErrors.product.notFoundBySku"


def test_add_item_twice_returns_409(client: TestClient, db, admin_headers):
    """Adding the same SKU twice is a conflict; the operator
    probably scanned a barcode that matched a row already in the
    session."""
    sku = _seed_product(db, on_hand=10)
    session = _start_session(client, admin_headers)
    client.post(
        f"/api/v1/inventory-counts/{session['id']}/items",
        json={"sku": sku}, headers=admin_headers,
    )
    resp = client.post(
        f"/api/v1/inventory-counts/{session['id']}/items",
        json={"sku": sku}, headers=admin_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "apiErrors.inventoryCount.skuAlreadyInSession"


def test_update_count_sets_value_and_clears_value(
    client: TestClient, db, admin_headers,
):
    """PATCH with a number sets the count; PATCH with null clears
    it (operator scanned but hasn't counted yet)."""
    sku = _seed_product(db, on_hand=10)
    session = _start_session(client, admin_headers)
    add = client.post(
        f"/api/v1/inventory-counts/{session['id']}/items",
        json={"sku": sku}, headers=admin_headers,
    )
    item_id = add.json()["id"]

    resp = client.patch(
        f"/api/v1/inventory-counts/{session['id']}/items/{item_id}",
        json={"counted_quantity": 8},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["counted_quantity"] == 8

    resp = client.patch(
        f"/api/v1/inventory-counts/{session['id']}/items/{item_id}",
        json={"counted_quantity": None},
        headers=admin_headers,
    )
    assert resp.json()["counted_quantity"] is None


def test_update_count_rejects_negative_quantity(
    client: TestClient, db, admin_headers,
):
    sku = _seed_product(db, on_hand=10)
    session = _start_session(client, admin_headers)
    add = client.post(
        f"/api/v1/inventory-counts/{session['id']}/items",
        json={"sku": sku}, headers=admin_headers,
    )
    item_id = add.json()["id"]

    resp = client.patch(
        f"/api/v1/inventory-counts/{session['id']}/items/{item_id}",
        json={"counted_quantity": -3},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "apiErrors.inventoryCount.negativeCount"


def test_delete_item_removes_a_mistaken_add(
    client: TestClient, db, admin_headers,
):
    sku = _seed_product(db, on_hand=10)
    session = _start_session(client, admin_headers)
    add = client.post(
        f"/api/v1/inventory-counts/{session['id']}/items",
        json={"sku": sku}, headers=admin_headers,
    )
    item_id = add.json()["id"]

    resp = client.delete(
        f"/api/v1/inventory-counts/{session['id']}/items/{item_id}",
        headers=admin_headers,
    )
    assert resp.status_code == 204
    # Detail no longer carries the row.
    detail = client.get(
        f"/api/v1/inventory-counts/{session['id']}", headers=admin_headers,
    ).json()
    assert detail["items"] == []


# ---------------------------------------------------------------------------
# Commit math
# ---------------------------------------------------------------------------


def test_commit_writes_recount_adjustments_for_deltas(
    client: TestClient, db, admin_headers,
):
    """Two items with non-zero deltas + one zero-delta + one
    NULL-counted. Commit writes 2 adjustments; skips 2."""
    sku_low = _seed_product(db, on_hand=10)   # operator counts 7 → -3
    sku_high = _seed_product(db, on_hand=5)   # operator counts 8 → +3
    sku_match = _seed_product(db, on_hand=20) # operator counts 20 → 0 (skip)
    sku_skip = _seed_product(db, on_hand=12)  # operator never counts (skip)

    session = _start_session(client, admin_headers)
    sid = session["id"]

    def _add_and_count(sku: str, counted: int | None) -> int:
        add = client.post(
            f"/api/v1/inventory-counts/{sid}/items",
            json={"sku": sku}, headers=admin_headers,
        )
        iid = add.json()["id"]
        if counted is not None:
            client.patch(
                f"/api/v1/inventory-counts/{sid}/items/{iid}",
                json={"counted_quantity": counted},
                headers=admin_headers,
            )
        return iid

    _add_and_count(sku_low, 7)
    _add_and_count(sku_high, 8)
    _add_and_count(sku_match, 20)
    _add_and_count(sku_skip, None)

    resp = client.post(
        f"/api/v1/inventory-counts/{sid}/commit",
        headers=admin_headers,
    )
    body = resp.json()
    assert resp.status_code == 200
    assert body["adjustments_created"] == 2
    assert body["items_skipped"] == 2
    assert body["session"]["status"] == "committed"
    assert body["session"]["ended_at"] is not None

    # Verify the adjustment rows landed with the right deltas + code.
    adjustments = (
        db.query(InventoryAdjustment)
        .filter(InventoryAdjustment.reason.like(f"Physical count session #{sid}%"))
        .all()
    )
    assert len(adjustments) == 2
    deltas = sorted(adj.adjustment for adj in adjustments)
    assert deltas == [-3, 3]
    assert all(adj.reason_code == "recount" for adj in adjustments)


def test_commit_updates_on_hand_inventory(
    client: TestClient, db, admin_headers,
):
    """End-to-end: the recount adjustment flows through to the
    actual InventoryItem.quantity column."""
    sku = _seed_product(db, on_hand=50)
    product = crud_product.product.get_by_sku(db, sku=sku)
    session = _start_session(client, admin_headers)
    add = client.post(
        f"/api/v1/inventory-counts/{session['id']}/items",
        json={"sku": sku}, headers=admin_headers,
    )
    client.patch(
        f"/api/v1/inventory-counts/{session['id']}/items/{add.json()['id']}",
        json={"counted_quantity": 47},
        headers=admin_headers,
    )
    client.post(
        f"/api/v1/inventory-counts/{session['id']}/commit",
        headers=admin_headers,
    )

    db.expire_all()
    inv = (
        db.query(InventoryItem)
        .filter(InventoryItem.product_id == product.id)
        .filter(InventoryItem.location == "default")
        .first()
    )
    assert inv.quantity == 47


def test_commit_idempotent_on_already_committed(
    client: TestClient, db, admin_headers,
):
    """A second commit on a committed session is 409, not a silent
    double-write. The audit row + status guard make this safe."""
    sku = _seed_product(db, on_hand=10)
    session = _start_session(client, admin_headers)
    add = client.post(
        f"/api/v1/inventory-counts/{session['id']}/items",
        json={"sku": sku}, headers=admin_headers,
    )
    client.patch(
        f"/api/v1/inventory-counts/{session['id']}/items/{add.json()['id']}",
        json={"counted_quantity": 7},
        headers=admin_headers,
    )
    first = client.post(
        f"/api/v1/inventory-counts/{session['id']}/commit", headers=admin_headers,
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/inventory-counts/{session['id']}/commit", headers=admin_headers,
    )
    assert second.status_code == 409
    assert second.json()["code"] == "apiErrors.inventoryCount.sessionNotInProgress"


# ---------------------------------------------------------------------------
# Cancel + state machine
# ---------------------------------------------------------------------------


def test_cancel_session_writes_no_adjustments(
    client: TestClient, db, admin_headers,
):
    """Cancel is a no-op record — the session stays in the DB but
    no adjustments fire."""
    sku = _seed_product(db, on_hand=10)
    session = _start_session(client, admin_headers)
    add = client.post(
        f"/api/v1/inventory-counts/{session['id']}/items",
        json={"sku": sku}, headers=admin_headers,
    )
    client.patch(
        f"/api/v1/inventory-counts/{session['id']}/items/{add.json()['id']}",
        json={"counted_quantity": 999},  # would normally write +989
        headers=admin_headers,
    )

    resp = client.post(
        f"/api/v1/inventory-counts/{session['id']}/cancel",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    adjs = (
        db.query(InventoryAdjustment)
        .filter(InventoryAdjustment.reason.like(f"Physical count session #{session['id']}%"))
        .count()
    )
    assert adjs == 0


def test_cannot_add_item_to_committed_session(
    client: TestClient, db, admin_headers,
):
    sku = _seed_product(db, on_hand=10)
    session = _start_session(client, admin_headers)
    add = client.post(
        f"/api/v1/inventory-counts/{session['id']}/items",
        json={"sku": sku}, headers=admin_headers,
    )
    client.patch(
        f"/api/v1/inventory-counts/{session['id']}/items/{add.json()['id']}",
        json={"counted_quantity": 10},
        headers=admin_headers,
    )
    client.post(
        f"/api/v1/inventory-counts/{session['id']}/commit",
        headers=admin_headers,
    )

    sku2 = _seed_product(db, on_hand=5)
    resp = client.post(
        f"/api/v1/inventory-counts/{session['id']}/items",
        json={"sku": sku2}, headers=admin_headers,
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# List endpoint
# ---------------------------------------------------------------------------


def test_list_sessions_newest_first(client: TestClient, db, admin_headers):
    """Sessions are listed newest first so the operator's most
    recent in-progress count is right at the top."""
    sa = _start_session(client, admin_headers)
    sb = _start_session(client, admin_headers)
    resp = client.get("/api/v1/inventory-counts/", headers=admin_headers)
    ids = [s["id"] for s in resp.json()]
    assert ids[0] == sb["id"]
    assert sa["id"] in ids


def test_list_sessions_filters_by_status(
    client: TestClient, db, admin_headers,
):
    sa = _start_session(client, admin_headers)
    sb = _start_session(client, admin_headers)
    client.post(
        f"/api/v1/inventory-counts/{sb['id']}/cancel", headers=admin_headers,
    )

    resp = client.get(
        "/api/v1/inventory-counts/",
        params={"status": "in_progress"},
        headers=admin_headers,
    )
    ids = {s["id"] for s in resp.json()}
    assert sa["id"] in ids
    assert sb["id"] not in ids


def test_list_sessions_rejects_unknown_status(
    client: TestClient, admin_headers,
):
    resp = client.get(
        "/api/v1/inventory-counts/",
        params={"status": "purged"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "apiErrors.inventoryCount.unknownStatus"
