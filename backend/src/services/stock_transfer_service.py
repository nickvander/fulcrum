from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from src.crud.crud_stock_transfer import stock_transfer as crud_stock_transfer
from src.models.inventory import InventoryItem
from src.models.stock_transfer import StockTransfer, StockTransferStatus
from src.schemas.stock_transfer import StockTransferCreate, StockTransferUpdate


_EDITABLE_STATUSES = {StockTransferStatus.DRAFT.value}
_SHIPPABLE_STATUSES = {StockTransferStatus.DRAFT.value}
_RECEIVABLE_STATUSES = {
    StockTransferStatus.SHIPPED.value,
    StockTransferStatus.PARTIALLY_RECEIVED.value,
}


class StockTransferService:
    def create_draft(
        self,
        db: Session,
        *,
        transfer_in: StockTransferCreate,
        user=None,
    ) -> StockTransfer:
        if transfer_in.source_location == transfer_in.dest_location:
            raise HTTPException(
                status_code=400,
                detail="Source and destination locations must differ",
            )
        for item in transfer_in.items or []:
            if item.qty_planned <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Each line item must have qty_planned > 0",
                )

        return crud_stock_transfer.create_with_items(
            db=db,
            obj_in=transfer_in,
            created_by_id=getattr(user, "id", None),
        )

    def update_draft(
        self,
        db: Session,
        *,
        transfer_id: int,
        transfer_in: StockTransferUpdate,
    ) -> StockTransfer:
        transfer = self._get_or_404(db, transfer_id)
        if transfer.status not in _EDITABLE_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot edit a transfer in status '{transfer.status}'",
            )

        update_data = transfer_in.model_dump(exclude_unset=True)
        items_data = update_data.pop("items", None)

        for field, value in update_data.items():
            setattr(transfer, field, value)

        if transfer.source_location == transfer.dest_location:
            raise HTTPException(
                status_code=400,
                detail="Source and destination locations must differ",
            )

        db.add(transfer)
        db.commit()
        db.refresh(transfer)

        if items_data is not None:
            for item in items_data:
                qty = item["qty_planned"] if isinstance(item, dict) else item.qty_planned
                if qty <= 0:
                    raise HTTPException(
                        status_code=400,
                        detail="Each line item must have qty_planned > 0",
                    )
            transfer = crud_stock_transfer.replace_items(
                db=db, transfer=transfer, items_data=items_data
            )

        return transfer

    def ship(self, db: Session, *, transfer_id: int, user=None) -> StockTransfer:
        from src.services.inventory_service import inventory_service

        transfer = self._get_or_404(db, transfer_id)
        if transfer.status not in _SHIPPABLE_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot ship a transfer in status '{transfer.status}'",
            )

        if not transfer.items:
            raise HTTPException(
                status_code=400,
                detail="Cannot ship an empty transfer",
            )

        for item in transfer.items:
            current_qty = (
                db.query(func.coalesce(func.sum(InventoryItem.quantity), 0))
                .filter(
                    InventoryItem.product_id == item.product_id,
                    InventoryItem.variant_id == item.variant_id,
                    InventoryItem.location == transfer.source_location,
                )
                .scalar()
                or 0
            )
            if current_qty < item.qty_planned:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Insufficient stock at '{transfer.source_location}' for "
                        f"product {item.product_id}: need {item.qty_planned}, have {current_qty}"
                    ),
                )

        actor = self._actor_id(user)
        for item in transfer.items:
            inventory_service.adjust_stock(
                db=db,
                product_id=item.product_id,
                adjustment=-item.qty_planned,
                variant_id=item.variant_id,
                reason=f"Stock transfer #{transfer.id} shipped to {transfer.dest_location}",
                location=transfer.source_location,
                user_id=actor,
            )
            item.qty_shipped = item.qty_planned
            db.add(item)

        transfer.status = StockTransferStatus.SHIPPED.value
        transfer.shipped_at = datetime.now(timezone.utc)
        db.add(transfer)
        db.commit()
        db.refresh(transfer)
        return transfer

    def receive_items(
        self,
        db: Session,
        *,
        transfer_id: int,
        received_items: list,
        user=None,
    ) -> StockTransfer:
        from src.services.inventory_service import inventory_service

        transfer = self._get_or_404(db, transfer_id)
        if transfer.status not in _RECEIVABLE_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot receive a transfer in status '{transfer.status}'",
            )

        items_by_id = {item.id: item for item in transfer.items}
        items_by_product = {(item.product_id, item.variant_id): item for item in transfer.items}

        actor = self._actor_id(user)
        applied = 0
        for entry in received_items:
            if isinstance(entry, dict):
                xid = entry.get("transfer_item_id")
                pid = entry.get("product_id")
                vid = entry.get("variant_id")
                qty = entry.get("quantity")
            else:
                xid = getattr(entry, "transfer_item_id", None)
                pid = getattr(entry, "product_id", None)
                vid = getattr(entry, "variant_id", None)
                qty = getattr(entry, "quantity", None)

            if qty is None or qty <= 0:
                continue

            item = items_by_id.get(xid) if xid else None
            if not item and pid is not None:
                item = items_by_product.get((pid, vid))
            if not item:
                continue

            already_received = item.qty_received or 0
            shipped = item.qty_shipped or 0
            remaining = max(0, shipped - already_received)
            if qty > remaining:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Cannot receive {qty} units for transfer item {item.id}; "
                        f"only {remaining} remaining (shipped={shipped}, received={already_received})"
                    ),
                )

            inventory_service.adjust_stock(
                db=db,
                product_id=item.product_id,
                adjustment=qty,
                variant_id=item.variant_id,
                reason=f"Stock transfer #{transfer.id} received at {transfer.dest_location}",
                location=transfer.dest_location,
                user_id=actor,
            )
            item.qty_received = already_received + qty
            db.add(item)
            applied += 1

        if applied == 0:
            raise HTTPException(status_code=400, detail="No valid receive lines provided")

        db.commit()
        db.refresh(transfer)
        return self._apply_receiving_status(db, transfer)

    def cancel(self, db: Session, *, transfer_id: int) -> StockTransfer:
        transfer = self._get_or_404(db, transfer_id)
        if transfer.status != StockTransferStatus.DRAFT.value:
            raise HTTPException(
                status_code=400,
                detail=f"Only draft transfers can be cancelled; this one is '{transfer.status}'",
            )
        transfer.status = StockTransferStatus.CANCELLED.value
        db.add(transfer)
        db.commit()
        db.refresh(transfer)
        return transfer

    def delete_draft(self, db: Session, *, transfer_id: int) -> None:
        transfer = self._get_or_404(db, transfer_id)
        if transfer.status not in (
            StockTransferStatus.DRAFT.value,
            StockTransferStatus.CANCELLED.value,
        ):
            raise HTTPException(
                status_code=400,
                detail="Only draft or cancelled transfers can be deleted",
            )
        db.delete(transfer)
        db.commit()

    def _apply_receiving_status(self, db: Session, transfer: StockTransfer) -> StockTransfer:
        if not transfer.items:
            return transfer

        all_full = True
        any_received = False
        for item in transfer.items:
            received = item.qty_received or 0
            shipped = item.qty_shipped or 0
            if received > 0:
                any_received = True
            if received < shipped:
                all_full = False

        new_status = transfer.status
        if all_full:
            new_status = StockTransferStatus.RECEIVED.value
        elif any_received:
            new_status = StockTransferStatus.PARTIALLY_RECEIVED.value

        if new_status != transfer.status:
            transfer.status = new_status
            if new_status == StockTransferStatus.RECEIVED.value:
                transfer.received_at = datetime.now(timezone.utc)
            db.add(transfer)
            db.commit()
            db.refresh(transfer)
        return transfer

    def _get_or_404(self, db: Session, transfer_id: int) -> StockTransfer:
        transfer = crud_stock_transfer.get(db=db, id=transfer_id)
        if not transfer:
            raise HTTPException(status_code=404, detail="Stock transfer not found")
        return transfer

    @staticmethod
    def _actor_id(user) -> Optional[str]:
        if user is None:
            return "system"
        return getattr(user, "email", None) or "system"


stock_transfer_service = StockTransferService()
