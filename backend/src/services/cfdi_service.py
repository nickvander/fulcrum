"""SAT/CFDI factura export (B7), export-only v1.

Two responsibilities:

  * issuer (emisor) config read/save, stored in `StoreSettings.settings`
    JSON under the "cfdi" key (mirrors how SMTP config is stored — no
    migration), and
  * building a CFDI 4.0-ready export of realized sales.

v1 issues every order to the RFC genérico ("PÚBLICO EN GENERAL"), the
standard treatment for consumer marketplace sales (factura global). MX
consumer prices are IVA-inclusive, so the line amounts are treated as
tax-inclusive and the IVA is backed out:

    base = amount / (1 + iva_rate)
    iva  = amount - base

Per-buyer specific-RFC capture and PAC timbrado are deferred.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.crud.crud_store_settings import store_settings as crud_store_settings
from src.models.order import SalesOrder, SalesOrderItem
from src.models.product import Product
from src.schemas.cfdi import (
    CfdiConcept,
    CfdiIssuerConfig,
    CfdiIssuerConfigUpdate,
    CfdiOrderRow,
    CfdiReport,
)

# Realized-sales statuses — mirrors the other reports so the factura
# export and the margin rollups agree on what counts as a sale.
_REALIZED_ORDER_STATUSES = ("COMPLETED", "SHIPPED")

# SAT RFC genérico for "público en general" (consumer sales).
RFC_GENERICO = "XAXX010101000"
RECEIVER_PUBLICO_GENERAL = "PÚBLICO EN GENERAL"

_DEFAULTS = {
    "default_product_key": "01010101",
    "default_unit_key": "H87",
    "cfdi_use": "S01",
    "iva_rate": 0.16,
}

# FP-06: default per-channel invoicing policy. ML defaults to
# marketplace_handled (ML's "facturación automática" stamps those orders;
# Fulcrum only links the UUID). Storefront + Amazon default to self-stamp.
DEFAULT_INVOICING_POLICY = {
    "MERCADOLIBRE": "marketplace_handled",
    "AMAZON": "self",
    "FULCRUM": "self",
}


def read_issuer_config(db: Session) -> CfdiIssuerConfig:
    settings = crud_store_settings.get_settings(db)
    raw = (settings.settings or {}).get("cfdi", {}) if settings else {}
    rfc = raw.get("rfc")
    policy = {
        **DEFAULT_INVOICING_POLICY,
        **{k.upper(): v for k, v in (raw.get("invoicing_policy") or {}).items()},
    }
    return CfdiIssuerConfig(
        rfc=rfc,
        name=raw.get("name"),
        tax_regime=raw.get("tax_regime"),
        postal_code=raw.get("postal_code"),
        default_product_key=raw.get("default_product_key", _DEFAULTS["default_product_key"]),
        default_unit_key=raw.get("default_unit_key", _DEFAULTS["default_unit_key"]),
        cfdi_use=raw.get("cfdi_use", _DEFAULTS["cfdi_use"]),
        iva_rate=float(raw.get("iva_rate", _DEFAULTS["iva_rate"])),
        # "configured" means the legally-required emisor fields are present.
        is_configured=bool(rfc and raw.get("name") and raw.get("tax_regime")),
        invoicing_policy=policy,
        pac_vendor=raw.get("pac_vendor"),
        pac_sandbox=bool(raw.get("pac_sandbox", True)),
        pac_configured=bool(raw.get("pac_api_key_encrypted")),
    )


def save_issuer_config(db: Session, update: CfdiIssuerConfigUpdate) -> CfdiIssuerConfig:
    from src.core.encryption import encryption_service

    settings = crud_store_settings.get_settings(db)
    existing = dict((settings.settings or {}).get("cfdi", {}))
    patch = update.model_dump(exclude_unset=True)
    # The PAC API key is a secret — encrypt it and never store/return raw.
    pac_key = patch.pop("pac_api_key", None)
    if pac_key:
        existing["pac_api_key_encrypted"] = encryption_service.encrypt(pac_key)
    existing.update({k: v for k, v in patch.items() if v is not None})
    # Reassign a NEW dict so SQLAlchemy flags the JSON column dirty.
    settings.settings = {**(settings.settings or {}), "cfdi": existing}
    db.commit()
    db.refresh(settings)
    return read_issuer_config(db)


def resolve_pac_api_key(db: Session) -> Optional[str]:
    """Decrypted PAC API key, or None when not configured."""
    from src.core.encryption import encryption_service

    settings = crud_store_settings.get_settings(db)
    enc = (settings.settings or {}).get("cfdi", {}).get("pac_api_key_encrypted")
    if not enc:
        return None
    try:
        return encryption_service.decrypt(enc)
    except Exception:  # noqa: BLE001 — a corrupt/rotated key shouldn't 500 the caller
        return None


def _backout_iva(amount: float, iva_rate: float) -> tuple[float, float]:
    """Split a tax-inclusive amount into (base, iva)."""
    if iva_rate <= 0:
        return round(amount, 2), 0.0
    base = amount / (1.0 + iva_rate)
    return round(base, 2), round(amount - base, 2)


def build_cfdi_report(
    db: Session,
    *,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 1000,
) -> CfdiReport:
    """Realized sales in the date range, in a CFDI-ready shape."""
    issuer = read_issuer_config(db)
    iva_rate = issuer.iva_rate

    q = (
        db.query(SalesOrder)
        .filter(SalesOrder.status.in_(_REALIZED_ORDER_STATUSES))
        .order_by(SalesOrder.created_at.asc())
    )
    if start_date is not None:
        q = q.filter(SalesOrder.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date is not None:
        q = q.filter(SalesOrder.created_at <= datetime.combine(end_date, datetime.max.time()))
    orders = q.limit(limit).all()

    order_ids = [o.id for o in orders]
    items_by_order: dict[int, list] = {oid: [] for oid in order_ids}
    if order_ids:
        item_rows = (
            db.query(SalesOrderItem, Product.name)
            .outerjoin(Product, Product.id == SalesOrderItem.product_id)
            .filter(SalesOrderItem.order_id.in_(order_ids))
            .all()
        )
        for item, product_name in item_rows:
            items_by_order.setdefault(item.order_id, []).append((item, product_name))

    rows: list[CfdiOrderRow] = []
    grand_subtotal = grand_iva = grand_total = 0.0
    for order in orders:
        concepts: list[CfdiConcept] = []
        sub = iva = 0.0
        for item, product_name in items_by_order.get(order.id, []):
            qty = int(item.quantity or 0)
            unit_inc = float(item.price_per_unit or 0.0)
            line_inc = unit_inc * qty
            base, line_iva = _backout_iva(line_inc, iva_rate)
            unit_base, _ = _backout_iva(unit_inc, iva_rate)
            concepts.append(
                CfdiConcept(
                    description=product_name or f"Producto {item.product_id}",
                    product_key=issuer.default_product_key,
                    unit_key=issuer.default_unit_key,
                    quantity=qty,
                    unit_price=unit_base,
                    amount=base,
                    iva_amount=line_iva,
                )
            )
            sub += base
            iva += line_iva

        # A CFDI must satisfy Total = SubTotal + taxes, so derive the
        # total from the rounded components instead of independently
        # summing the tax-inclusive line amounts (which can drift by a
        # cent across multiple concepts and make the document invalid).
        row_subtotal = round(sub, 2)
        row_iva = round(iva, 2)
        row_total = round(row_subtotal + row_iva, 2)

        rows.append(
            CfdiOrderRow(
                order_id=order.id,
                external_order_id=order.external_order_id,
                issued_at=order.created_at,
                source=order.source,
                currency=order.currency or "MXN",
                receiver_rfc=RFC_GENERICO,
                receiver_name=RECEIVER_PUBLICO_GENERAL,
                cfdi_use=issuer.cfdi_use,
                concepts=concepts,
                subtotal=row_subtotal,
                iva_amount=row_iva,
                total=row_total,
            )
        )
        # Accumulate the rounded per-row figures so the grand totals stay
        # internally consistent too (subtotal + iva == total).
        grand_subtotal = round(grand_subtotal + row_subtotal, 2)
        grand_iva = round(grand_iva + row_iva, 2)
        grand_total = round(grand_total + row_total, 2)

    return CfdiReport(
        rows=rows,
        issuer=issuer,
        start_date=start_date.isoformat() if start_date else None,
        end_date=end_date.isoformat() if end_date else None,
        order_count=len(rows),
        subtotal=grand_subtotal,
        iva_amount=grand_iva,
        total=grand_total,
    )
