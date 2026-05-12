from typing import Any

from sqlalchemy.orm import Session, selectinload

from src.crud.base import CRUDBase
from src.models.product import Product
from src.models.stock_transfer import StockTransfer, StockTransferItem
from src.schemas.stock_transfer import StockTransferCreate, StockTransferUpdate


class CRUDStockTransfer(CRUDBase[StockTransfer, StockTransferCreate, StockTransferUpdate]):
    def _read_loader_options(self):
        return (
            selectinload(self.model.items)
            .selectinload(StockTransferItem.product)
            .selectinload(Product.images),
        )

    def get(self, db: Session, id: Any) -> StockTransfer | None:
        return (
            db.query(self.model)
            .options(*self._read_loader_options())
            .filter(self.model.id == id)
            .first()
        )

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, status: str | None = None
    ) -> list[StockTransfer]:
        query = db.query(self.model).options(*self._read_loader_options())
        if status:
            query = query.filter(self.model.status == status)
        return (
            query.order_by(self.model.created_at.desc(), self.model.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_with_items(
        self, db: Session, *, obj_in: StockTransferCreate, created_by_id: int | None = None
    ) -> StockTransfer:
        items_data = obj_in.items or []
        transfer = StockTransfer(
            source_location=obj_in.source_location,
            dest_location=obj_in.dest_location,
            notes=obj_in.notes,
            created_by_id=created_by_id,
        )
        db.add(transfer)
        db.flush()

        for item_in in items_data:
            db.add(
                StockTransferItem(
                    transfer_id=transfer.id,
                    product_id=item_in.product_id,
                    variant_id=item_in.variant_id,
                    qty_planned=item_in.qty_planned,
                )
            )

        db.commit()
        db.refresh(transfer)
        return transfer

    def replace_items(
        self, db: Session, *, transfer: StockTransfer, items_data: list
    ) -> StockTransfer:
        db.query(StockTransferItem).filter(
            StockTransferItem.transfer_id == transfer.id
        ).delete()
        for item in items_data:
            product_id = item["product_id"] if isinstance(item, dict) else item.product_id
            variant_id = (
                item.get("variant_id") if isinstance(item, dict) else item.variant_id
            )
            qty_planned = (
                item["qty_planned"] if isinstance(item, dict) else item.qty_planned
            )
            db.add(
                StockTransferItem(
                    transfer_id=transfer.id,
                    product_id=product_id,
                    variant_id=variant_id,
                    qty_planned=qty_planned,
                )
            )
        db.commit()
        db.refresh(transfer)
        return transfer


stock_transfer = CRUDStockTransfer(StockTransfer)
