"""
Ad-hoc demonstration of how orders flow across marketplaces under the
unified catalog. Creates a small set of orders on different channels,
then exercises the cross-channel reports. Cleans up after itself.

Run inside the backend container:
    python -m scripts.demo_cross_marketplace
"""
from datetime import datetime

from src.database import SessionLocal
from src.models.order import OrderSource, SalesOrder, SalesOrderItem, SalesOrderReturn
from src.models.product import Product
from src.services import marketplace_catalog, order_cost_engine


TAG = "XDEMO-"  # prefix so cleanup only removes what we created


def line(label=""):
    print(f"\n{'='*68}\n{label}\n{'='*68}" if label else "-" * 68)


def main():
    db = SessionLocal()
    created_product_ids, created_order_ids = [], []
    try:
        # ---- Seed two products -------------------------------------------
        p_ml = Product(name=f"{TAG}Termo MX", sku=f"{TAG}TERMO", cost_price=80.0,
                       default_resale_price=199.0, currency="MXN")
        p_az = Product(name=f"{TAG}Gadget US", sku=f"{TAG}GADGET", cost_price=10.0,
                       default_resale_price=25.0, currency="USD")
        db.add_all([p_ml, p_az])
        db.flush()
        created_product_ids += [p_ml.id, p_az.id]

        # ---- Use case 1: orders arrive on different channels -------------
        # Two MercadoLibre orders, one Amazon order, one direct (FULCRUM).
        def make_order(source, product, qty, price):
            o = SalesOrder(status="COMPLETED", total_price=qty * price,
                           currency=product.currency, created_at=datetime.utcnow(),
                           source=source, external_order_id=f"{TAG}{source}-{product.id}-{qty}")
            db.add(o)
            db.flush()
            db.add(SalesOrderItem(order_id=o.id, product_id=product.id, quantity=qty,
                                  price_per_unit=price, cost_per_unit=product.cost_price))
            db.flush()
            db.refresh(o)
            order_cost_engine.upsert_breakdown(db, o)
            created_order_ids.append(o.id)
            return o

        ml1 = make_order(OrderSource.MERCADOLIBRE, p_ml, 3, 199.0)
        make_order(OrderSource.MERCADOLIBRE, p_ml, 1, 199.0)
        make_order(OrderSource.AMAZON, p_az, 5, 25.0)
        make_order(OrderSource.FULCRUM, p_ml, 2, 199.0)  # direct/storefront
        db.commit()

        line("USE CASE 1 — multi-channel intake (source is a plain string)")
        for o in db.query(SalesOrder).filter(SalesOrder.external_order_id.like(f"{TAG}%")).all():
            print(f"  order #{o.id:<4} source={o.source:<13} total={o.total_price:>8} {o.currency}")

        # ---- Use case 2: Sales by channel (catalog-driven axis) ----------
        line("USE CASE 2 — sales by channel  (every catalog source on a stable axis)")
        rows = (
            db.query(SalesOrder.source).filter(SalesOrder.external_order_id.like(f"{TAG}%")).all()
        )
        from collections import Counter
        counts = Counter(r[0] for r in rows)
        for src in marketplace_catalog.order_sources():
            print(f"  {src:<13} {counts.get(src, 0)} order(s)")

        # ---- Use case 3: Margin by channel (cost engine) -----------------
        line("USE CASE 3 — margin by channel  (net margin per channel)")
        for src in ("MERCADOLIBRE", "AMAZON", "FULCRUM"):
            roll = order_cost_engine.aggregate_rollup(db, window_days=1, source=src)
            print(f"  {src:<13} orders={roll['orders']} revenue={roll['revenue_amount_mxn']:>9.2f} "
                  f"fees={roll['marketplace_fees_amount']:>7.2f} net={roll['net_profit_amount']:>9.2f}")

        # ---- Use case 4: source filtering --------------------------------
        line("USE CASE 4 — filter orders by channel  (?source=MERCADOLIBRE)")
        ml_orders = (
            db.query(SalesOrder)
            .filter(SalesOrder.external_order_id.like(f"{TAG}%"))
            .filter(SalesOrder.source == "MERCADOLIBRE")
            .all()
        )
        print(f"  MERCADOLIBRE filter → {len(ml_orders)} order(s): {[o.id for o in ml_orders]}")

        # ---- Use case 5: returns attribute to the right channel ----------
        line("USE CASE 5 — record a return on the ML order → attributes to MERCADOLIBRE")
        db.add(SalesOrderReturn(order_id=ml1.id, product_id=p_ml.id, quantity=1,
                                received_at=datetime.utcnow(), reason="damaged"))
        db.commit()
        ret_rows = (
            db.query(SalesOrder.source, SalesOrderReturn.quantity)
            .join(SalesOrderReturn, SalesOrderReturn.order_id == SalesOrder.id)
            .filter(SalesOrder.external_order_id.like(f"{TAG}%"))
            .all()
        )
        for src, qty in ret_rows:
            print(f"  return: {qty} unit(s) on channel {src}")

        # ---- Use case 6: EXTENSIBILITY — add a marketplace at runtime ----
        line("USE CASE 6 — add 'Walmart' to the catalog → it's instantly a valid channel")
        from src.services.marketplace_catalog import MarketplaceDefinition, MARKETPLACE_CATALOG
        walmart = MarketplaceDefinition(
            key="walmart", display_name="Walmart", status="planned",
            supports_oauth=False, is_primary=False, recommended_region="MX",
            brand_color="#0071DC", order_source="WALMART", connector=None,
        )
        MARKETPLACE_CATALOG.append(walmart)  # simulate a code-level catalog addition
        try:
            print(f"  order_sources() now: {marketplace_catalog.order_sources()}")
            print(f"  is_valid_order_source('WALMART'): {marketplace_catalog.is_valid_order_source('WALMART')}")
            w = make_order("WALMART", p_ml, 4, 150.0)
            db.commit()
            print(f"  created Walmart order #{w.id} with source={w.source!r} — stored, no migration needed")
            roll = order_cost_engine.aggregate_rollup(db, window_days=1, source="WALMART")
            print(f"  margin-by-channel picks it up → WALMART orders={roll['orders']} "
                  f"revenue={roll['revenue_amount_mxn']:.2f}")
        finally:
            MARKETPLACE_CATALOG.remove(walmart)

        line("All cross-marketplace use cases ran successfully.")
    finally:
        # ---- cleanup -----------------------------------------------------
        db.query(SalesOrderReturn).filter(
            SalesOrderReturn.order_id.in_(created_order_ids or [-1])
        ).delete(synchronize_session=False)
        from src.models.order import OrderCostBreakdown
        db.query(OrderCostBreakdown).filter(
            OrderCostBreakdown.order_id.in_(created_order_ids or [-1])
        ).delete(synchronize_session=False)
        db.query(SalesOrderItem).filter(
            SalesOrderItem.order_id.in_(created_order_ids or [-1])
        ).delete(synchronize_session=False)
        db.query(SalesOrder).filter(
            SalesOrder.external_order_id.like(f"{TAG}%")
        ).delete(synchronize_session=False)
        db.query(Product).filter(Product.id.in_(created_product_ids or [-1])).delete(
            synchronize_session=False
        )
        db.commit()
        db.close()
        print("\n(cleaned up demo data)")


if __name__ == "__main__":
    main()
