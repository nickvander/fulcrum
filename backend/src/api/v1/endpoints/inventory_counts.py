"""Physical-count session endpoints.

Mounted at `/api/v1/inventory-counts`. The endpoint layer is thin:
auth + parse + delegate to `services/inventory_count_service.py`,
which owns the state-machine + validation logic.

Endpoints:
  - GET    /                          list sessions
  - POST   /                          start a new session
  - GET    /{id}                      session detail (with items)
  - POST   /{id}/items                add a SKU
  - PATCH  /{id}/items/{item_id}      update counted_quantity
  - DELETE /{id}/items/{item_id}      remove a mistakenly-added SKU
  - POST   /{id}/commit               commit (writes adjustments)
  - POST   /{id}/cancel               cancel (no-op record)
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api import dependencies
from src.database import get_db
from src.models.inventory import (
    InventoryCountSession,
    InventoryCountSessionItem,
    InventoryCountSessionStatus,
)
from src.models.user import User
from src.schemas.inventory_count import (
    InventoryCountCommitResult,
    InventoryCountItemAdd,
    InventoryCountItemRead,
    InventoryCountItemUpdate,
    InventoryCountSessionCreate,
    InventoryCountSessionDetail,
    InventoryCountSessionRead,
)
from src.services.inventory_count_service import (
    add_item_by_sku,
    cancel_session,
    commit_session,
    get_session_or_404,
    list_sessions,
    remove_item,
    start_session,
    update_count,
)


router = APIRouter()


def _serialize_item(item: InventoryCountSessionItem) -> InventoryCountItemRead:
    """Hydrate one item row into the read schema, joining product
    name/sku from the relationship so the UI doesn't need a follow-up
    call per row. The relationship is loaded lazily but cheap (one
    product per item, all live in the session's items list)."""
    product = item.product
    return InventoryCountItemRead(
        id=item.id,
        session_id=item.session_id,
        product_id=item.product_id,
        variant_id=item.variant_id,
        product_sku=product.sku if product else None,
        product_name=product.name if product else None,
        expected_quantity=item.expected_quantity,
        counted_quantity=item.counted_quantity,
        added_at=item.added_at,
        updated_at=item.updated_at,
    )


def _serialize_session_header(
    session: InventoryCountSession, db: Session,
) -> InventoryCountSessionRead:
    """Header-only view used by the list endpoint. Counts items in
    one extra query rather than loading them just to take len()."""
    count = (
        db.query(InventoryCountSessionItem)
        .filter(InventoryCountSessionItem.session_id == session.id)
        .count()
    )
    email: Optional[str] = None
    if session.started_by_user_id:
        # Single-row lookup; the operator usually only sees a handful
        # of sessions, so N+1 here is bounded.
        u = db.query(User).filter(User.id == session.started_by_user_id).first()
        if u is not None:
            email = u.email
    return InventoryCountSessionRead(
        id=session.id,
        status=session.status,
        location=session.location,
        notes=session.notes,
        started_at=session.started_at,
        ended_at=session.ended_at,
        started_by_user_id=session.started_by_user_id,
        started_by_email=email,
        item_count=count,
    )


def _serialize_session_detail(
    session: InventoryCountSession, db: Session,
) -> InventoryCountSessionDetail:
    """Detail view: header + items. The endpoint always reads from
    a fresh session row so the operator's last action is reflected."""
    db.refresh(session)
    header = _serialize_session_header(session, db)
    return InventoryCountSessionDetail(
        **header.model_dump(),
        items=[_serialize_item(it) for it in session.items],
    )


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@router.get("/", response_model=List[InventoryCountSessionRead])
def list_inventory_count_sessions(
    *,
    db: Session = Depends(get_db),
    status: Optional[str] = Query(
        None,
        description="Filter by session status (in_progress / committed / cancelled).",
    ),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(dependencies.get_current_active_user),
):
    """List count sessions, newest first."""
    if status is not None and status not in {s.value for s in InventoryCountSessionStatus}:
        from src.core.errors import LocalizedHTTPException
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.inventoryCount.unknownStatus",
            params={"status": status},
            detail=f"Unknown status '{status}'",
        )
    sessions = list_sessions(db, status=status, limit=limit)
    return [_serialize_session_header(s, db) for s in sessions]


@router.post("/", response_model=InventoryCountSessionDetail, status_code=201)
def create_inventory_count_session(
    *,
    db: Session = Depends(get_db),
    payload: InventoryCountSessionCreate,
    current_user: User = Depends(dependencies.get_current_active_user),
):
    """Start a new in-progress session. Returns the empty detail
    envelope so the UI can navigate straight into it."""
    session = start_session(
        db,
        actor=current_user,
        location=payload.location or "default",
        notes=payload.notes,
    )
    db.commit()
    return _serialize_session_detail(session, db)


@router.get("/{session_id}", response_model=InventoryCountSessionDetail)
def get_inventory_count_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user),
):
    """Get one session with all its items."""
    session = get_session_or_404(db, session_id)
    return _serialize_session_detail(session, db)


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


@router.post(
    "/{session_id}/items",
    response_model=InventoryCountItemRead,
    status_code=201,
)
def add_inventory_count_item(
    session_id: int,
    payload: InventoryCountItemAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user),
):
    """Add a SKU to an in-progress session. The service snapshots
    `expected_quantity` from the live `InventoryItem` at the session's
    location; the operator then sets `counted_quantity` via PATCH."""
    session = get_session_or_404(db, session_id)
    item = add_item_by_sku(db, session=session, sku=payload.sku)
    db.commit()
    db.refresh(item)
    return _serialize_item(item)


@router.patch(
    "/{session_id}/items/{item_id}",
    response_model=InventoryCountItemRead,
)
def update_inventory_count_item(
    session_id: int,
    item_id: int,
    payload: InventoryCountItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user),
):
    """Set the operator's physical count for one row."""
    session = get_session_or_404(db, session_id)
    item = update_count(
        db, session=session, item_id=item_id,
        counted_quantity=payload.counted_quantity,
    )
    db.commit()
    db.refresh(item)
    return _serialize_item(item)


@router.delete(
    "/{session_id}/items/{item_id}",
    status_code=204,
)
def delete_inventory_count_item(
    session_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user),
):
    """Drop a row the operator added by mistake. Only legal on
    in-progress sessions."""
    session = get_session_or_404(db, session_id)
    remove_item(db, session=session, item_id=item_id)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# Lifecycle: commit / cancel
# ---------------------------------------------------------------------------


@router.post(
    "/{session_id}/commit",
    response_model=InventoryCountCommitResult,
)
def commit_inventory_count_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user),
):
    """Commit the session: write `reason_code='recount'` adjustments
    for every item where counted_quantity != expected_quantity, then
    flip the session to `committed`. Idempotent — a re-call against a
    `committed` session returns 409."""
    session = get_session_or_404(db, session_id)
    adjustments_created, items_skipped = commit_session(
        db, session=session, actor=current_user,
    )
    db.commit()
    return InventoryCountCommitResult(
        adjustments_created=adjustments_created,
        items_skipped=items_skipped,
        session=_serialize_session_detail(session, db),
    )


@router.post(
    "/{session_id}/cancel",
    response_model=InventoryCountSessionDetail,
)
def cancel_inventory_count_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user),
):
    """Cancel an in-progress session without writing any
    adjustments. The session row persists for audit."""
    session = get_session_or_404(db, session_id)
    cancel_session(db, session=session)
    db.commit()
    return _serialize_session_detail(session, db)
