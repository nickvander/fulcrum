"""CSV + PDF exports for the velocity / margin / stockout reports.

All three reports share an aggregation pass over SalesOrderItem joined
to SalesOrder filtered to status IN ("COMPLETED", "SHIPPED") within the
configured window. These tests share a fixture that seeds three
products in three distinct sales states (high-velocity, low-velocity,
zero-velocity) so each report sees a meaningful mix without re-seeding.
"""
import csv
import io
import re
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.inventory import InventoryItem
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.models.product import Product


@pytest.fixture
def seeded_sales(db: Session) -> dict[str, Product]:
    """Seed three products with distinct realized-sales footprints:

    - HOT: 30 units sold over the last 10 days (high velocity), 5 on hand
    - SLOW: 3 units sold over the last 20 days (low velocity), 50 on hand
    - DEAD: 0 units sold, 100 on hand — included so velocity/stockout
      ordering can show how zero-sales products are handled.

    Also seeds one PENDING order with 1000 units against HOT to assert
    that the realized-status filter (`COMPLETED` / `SHIPPED`) is honored
    — pending orders must NOT inflate revenue or velocity.
    """
    hot = Product(
        name="Hot Mover", sku="HOT-1",
        default_resale_price=20.00, cost_price=5.00, is_bundle=False,
        category="Movers",
    )
    slow = Product(
        name="Slow Mover", sku="SLOW-1",
        default_resale_price=10.00, cost_price=4.00, is_bundle=False,
        category="Movers",
    )
    dead = Product(
        name="Dead Stock", sku="DEAD-1",
        default_resale_price=15.00, cost_price=7.00, is_bundle=False,
        category="Other",
    )
    bundle = Product(
        name="Bundle Excluded", sku="BUNDLE-X",
        default_resale_price=99.00, cost_price=40.00, is_bundle=True,
    )
    db.add_all([hot, slow, dead, bundle])
    db.flush()

    db.add_all([
        InventoryItem(product_id=hot.id,  quantity=5,   location="default"),
        InventoryItem(product_id=slow.id, quantity=50,  location="default"),
        InventoryItem(product_id=dead.id, quantity=100, location="default"),
    ])

    now = datetime.utcnow()
    hot_order = SalesOrder(
        status="COMPLETED", total_price=600.00,
        created_at=now - timedelta(days=5),
        source=OrderSource.FULCRUM, external_order_id="HOT-COMP-1",
    )
    slow_order = SalesOrder(
        status="SHIPPED", total_price=30.00,
        created_at=now - timedelta(days=15),
        source=OrderSource.FULCRUM, external_order_id="SLOW-SHIP-1",
    )
    pending_order = SalesOrder(
        # Unrealized: must NOT affect velocity or revenue.
        status="PENDING", total_price=20000.00,
        created_at=now - timedelta(days=1),
        source=OrderSource.FULCRUM, external_order_id="HOT-PEND-1",
    )
    db.add_all([hot_order, slow_order, pending_order])
    db.flush()

    db.add_all([
        SalesOrderItem(order_id=hot_order.id,     product_id=hot.id,  quantity=30, price_per_unit=20.00),
        SalesOrderItem(order_id=slow_order.id,    product_id=slow.id, quantity=3,  price_per_unit=10.00),
        SalesOrderItem(order_id=pending_order.id, product_id=hot.id,  quantity=1000, price_per_unit=20.00),
    ])
    db.commit()

    return {"hot": hot, "slow": slow, "dead": dead, "bundle": bundle}


# ---------------------------------------------------------------------------
# Velocity report
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_velocity_csv_ranks_top_movers_first(
    client: TestClient, admin_headers: dict, seeded_sales: dict[str, Product]
):
    """HOT (3.0/day over 10d) outranks SLOW (0.15/day), and DEAD shows up
    at the bottom with daily_velocity=0 + days_left=999. Sort is
    descending by daily_velocity."""
    response = client.get(
        "/api/v1/reports/velocity/export",
        params={"window_days": 10},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    cd = response.headers["content-disposition"]
    assert re.search(r'filename="fulcrum-velocity-\d{4}-\d{2}-\d{2}\.csv"', cd)

    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == [
        "product_id", "product_sku", "product_name", "category",
        "on_hand", "units_sold", "daily_velocity", "days_of_inventory",
    ]

    sku_order = [row[1] for row in rows[1:] if row[1] in ("HOT-1", "SLOW-1", "DEAD-1")]
    assert sku_order[:2] == ["HOT-1", "SLOW-1"]   # top movers
    assert "DEAD-1" in sku_order                  # but no-sales row is still present

    body_by_sku = {row[1]: row for row in rows[1:]}
    hot = body_by_sku["HOT-1"]
    assert hot[4] == "5"        # on_hand
    assert hot[5] == "30"       # units_sold (the PENDING 1000 doesn't count)
    assert hot[6] == "3.00"     # daily_velocity over 10d = 30/10
    assert hot[7] == "1.7"      # days_of_inventory = 5/3.0 = 1.67 → rounded 1.7

    dead = body_by_sku["DEAD-1"]
    assert dead[5] == "0"
    assert dead[6] == "0.00"
    assert dead[7] == "999.0"


@pytest.mark.db
def test_velocity_excludes_bundles(
    client: TestClient, admin_headers: dict, seeded_sales: dict[str, Product]
):
    """Bundles are excluded — same convention as inventory-snapshot."""
    response = client.get("/api/v1/reports/velocity/export", headers=admin_headers)
    rows = list(csv.reader(io.StringIO(response.text)))
    assert all(row[1] != "BUNDLE-X" for row in rows[1:])


@pytest.mark.db
def test_velocity_window_filter_excludes_old_sales(
    client: TestClient, admin_headers: dict, seeded_sales: dict[str, Product]
):
    """Sales outside the window must not count. With window=3, SLOW's
    sale (15d ago) drops out, but HOT's (5d ago) stays."""
    response = client.get(
        "/api/v1/reports/velocity/export",
        params={"window_days": 3},
        headers=admin_headers,
    )
    rows = list(csv.reader(io.StringIO(response.text)))
    body_by_sku = {row[1]: row for row in rows[1:]}
    # HOT's 5-day-old order is also outside a 3-day window, so 0 units.
    assert body_by_sku["HOT-1"][5] == "0"
    assert body_by_sku["SLOW-1"][5] == "0"


@pytest.mark.db
def test_velocity_pdf_renders(
    client: TestClient, admin_headers: dict, seeded_sales: dict[str, Product]
):
    response = client.get("/api/v1/reports/velocity/export-pdf", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF-")
    assert response.content.rstrip().endswith(b"%%EOF")


# ---------------------------------------------------------------------------
# Margin report
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_margin_csv_includes_revenue_cost_and_pct(
    client: TestClient, admin_headers: dict, seeded_sales: dict[str, Product]
):
    """HOT: 30 * $20 = $600 revenue, 30 * $5 = $150 cost → $450 margin
    (75%). SLOW: 3 * $10 = $30 revenue, 3 * $4 = $12 cost → $18 margin
    (60%). DEAD has zero sales so it should NOT appear at all (the
    margin report excludes zero rows, unlike velocity)."""
    response = client.get(
        "/api/v1/reports/margin/export",
        params={"window_days": 30},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    cd = response.headers["content-disposition"]
    assert re.search(r'filename="fulcrum-margin-\d{4}-\d{2}-\d{2}\.csv"', cd)

    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == [
        "product_id", "product_sku", "product_name", "category",
        "units_sold", "revenue", "cost", "gross_margin", "margin_pct",
    ]
    body_by_sku = {row[1]: row for row in rows[1:]}

    # DEAD (no sales) must NOT appear in the margin report.
    assert "DEAD-1" not in body_by_sku
    # Bundle excluded as well.
    assert "BUNDLE-X" not in body_by_sku

    hot = body_by_sku["HOT-1"]
    assert hot[4] == "30"
    assert hot[5] == "USD 600.00"
    assert hot[6] == "USD 150.00"
    assert hot[7] == "USD 450.00"
    assert hot[8] == "75.0%"

    slow = body_by_sku["SLOW-1"]
    assert slow[5] == "USD 30.00"
    assert slow[6] == "USD 12.00"
    assert slow[7] == "USD 18.00"
    assert slow[8] == "60.0%"


@pytest.mark.db
def test_margin_ranks_by_gross_margin_descending(
    client: TestClient, admin_headers: dict, seeded_sales: dict[str, Product]
):
    response = client.get("/api/v1/reports/margin/export", headers=admin_headers)
    rows = list(csv.reader(io.StringIO(response.text)))
    sku_order = [row[1] for row in rows[1:]]
    # HOT margin = $450 > SLOW margin = $18 → HOT first.
    assert sku_order.index("HOT-1") < sku_order.index("SLOW-1")


@pytest.mark.db
def test_margin_excludes_unrealized_orders(
    client: TestClient, admin_headers: dict, seeded_sales: dict[str, Product]
):
    """The PENDING order in the fixture (1000 units against HOT) must
    not contribute to revenue. Without the status filter, HOT's row
    would be ~$20,600."""
    response = client.get("/api/v1/reports/margin/export", headers=admin_headers)
    rows = list(csv.reader(io.StringIO(response.text)))
    body_by_sku = {row[1]: row for row in rows[1:]}
    assert body_by_sku["HOT-1"][5] == "USD 600.00"


@pytest.mark.db
def test_margin_pdf_renders(
    client: TestClient, admin_headers: dict, seeded_sales: dict[str, Product]
):
    response = client.get("/api/v1/reports/margin/export-pdf", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF-")


@pytest.mark.db
def test_margin_empty_window_returns_header_only(
    client: TestClient, admin_headers: dict, db: Session
):
    """A clean window (no orders) must still return a 200 with just the
    header row — accountants want a stamped 'nothing to report' rather
    than an error."""
    response = client.get(
        "/api/v1/reports/margin/export",
        params={"window_days": 30},
        headers=admin_headers,
    )
    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.text)))
    assert len(rows) == 1
    assert rows[0][0] == "product_id"


# ---------------------------------------------------------------------------
# Stockout report
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_stockout_flags_out_imminent_and_excludes_well_stocked(
    client: TestClient, admin_headers: dict, db: Session
):
    """Three products in three states:
      - out: on_hand=0, any velocity → "out"
      - imminent: 5 on hand, 3/day velocity → 1.7 days_left → "imminent"
      - well-stocked: 100 on hand, no velocity → 999 days → excluded"""
    p_out = Product(name="Out", sku="OUT-1", cost_price=1.0, is_bundle=False)
    p_imm = Product(name="Imminent", sku="IMM-1", cost_price=1.0, is_bundle=False)
    p_safe = Product(name="Safe", sku="SAFE-1", cost_price=1.0, is_bundle=False)
    db.add_all([p_out, p_imm, p_safe])
    db.flush()
    db.add_all([
        InventoryItem(product_id=p_out.id,  quantity=0,   location="default"),
        InventoryItem(product_id=p_imm.id,  quantity=5,   location="default"),
        InventoryItem(product_id=p_safe.id, quantity=100, location="default"),
    ])
    order = SalesOrder(
        status="COMPLETED", total_price=600.0,
        created_at=datetime.utcnow() - timedelta(days=2),
        source=OrderSource.FULCRUM, external_order_id="IMM-1",
    )
    db.add(order)
    db.flush()
    # 30 units in last 10 days → 3/day velocity → 5 / 3 = 1.7 days_left
    db.add(SalesOrderItem(order_id=order.id, product_id=p_imm.id, quantity=30, price_per_unit=20.0))
    db.commit()

    response = client.get(
        "/api/v1/reports/stockout/export",
        params={"window_days": 10, "imminent_days": 7, "watch_days": 14},
        headers=admin_headers,
    )
    assert response.status_code == 200

    cd = response.headers["content-disposition"]
    assert re.search(r'filename="fulcrum-stockout-\d{4}-\d{2}-\d{2}\.csv"', cd)

    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == [
        "product_id", "product_sku", "product_name", "severity",
        "on_hand", "daily_velocity", "days_of_inventory",
    ]

    body_by_sku = {row[1]: row for row in rows[1:]}
    assert body_by_sku["OUT-1"][3] == "out"
    assert body_by_sku["OUT-1"][4] == "0"

    assert body_by_sku["IMM-1"][3] == "imminent"
    assert body_by_sku["IMM-1"][5] == "3.00"
    assert body_by_sku["IMM-1"][6] == "1.7"

    # SAFE has no velocity and plenty of stock → excluded
    assert "SAFE-1" not in body_by_sku


@pytest.mark.db
def test_stockout_orders_out_before_imminent_before_watch(
    client: TestClient, admin_headers: dict, db: Session
):
    """The buyer scans top-down — most urgent must appear first."""
    p_watch = Product(name="Watch", sku="WATCH-1", cost_price=1.0, is_bundle=False)
    p_out = Product(name="Out2", sku="OUT-2", cost_price=1.0, is_bundle=False)
    p_imm = Product(name="Imm2", sku="IMM-2", cost_price=1.0, is_bundle=False)
    db.add_all([p_watch, p_out, p_imm])
    db.flush()
    db.add_all([
        InventoryItem(product_id=p_watch.id, quantity=130, location="default"),
        InventoryItem(product_id=p_out.id,   quantity=0,   location="default"),
        InventoryItem(product_id=p_imm.id,   quantity=5,   location="default"),
    ])
    order = SalesOrder(
        status="COMPLETED", total_price=10.0,
        created_at=datetime.utcnow() - timedelta(days=1),
        source=OrderSource.FULCRUM, external_order_id="ORDER-ORDER-1",
    )
    db.add(order)
    db.flush()
    db.add_all([
        SalesOrderItem(order_id=order.id, product_id=p_watch.id, quantity=100, price_per_unit=1.0),
        SalesOrderItem(order_id=order.id, product_id=p_imm.id,   quantity=30,  price_per_unit=1.0),
    ])
    db.commit()

    response = client.get(
        "/api/v1/reports/stockout/export",
        params={"window_days": 10, "imminent_days": 7, "watch_days": 14},
        headers=admin_headers,
    )
    rows = list(csv.reader(io.StringIO(response.text)))
    sku_order = [row[1] for row in rows[1:] if row[1] in ("OUT-2", "IMM-2", "WATCH-1")]
    assert sku_order == ["OUT-2", "IMM-2", "WATCH-1"]


@pytest.mark.db
def test_stockout_empty_when_everything_well_stocked(
    client: TestClient, admin_headers: dict, db: Session
):
    p = Product(name="Plenty", sku="PLENTY-1", cost_price=1.0, is_bundle=False)
    db.add(p)
    db.flush()
    db.add(InventoryItem(product_id=p.id, quantity=10000, location="default"))
    db.commit()

    response = client.get("/api/v1/reports/stockout/export", headers=admin_headers)
    rows = list(csv.reader(io.StringIO(response.text)))
    assert len(rows) == 1
    assert rows[0][0] == "product_id"


@pytest.mark.db
def test_stockout_pdf_renders(
    client: TestClient, admin_headers: dict, db: Session
):
    p = Product(name="OUT4PDF", sku="OUT-PDF", cost_price=1.0, is_bundle=False)
    db.add(p)
    db.flush()
    db.add(InventoryItem(product_id=p.id, quantity=0, location="default"))
    db.commit()

    response = client.get("/api/v1/reports/stockout/export-pdf", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF-")


# ---------------------------------------------------------------------------
# Margin report: historical cost-at-sale (migration 5d9f2a3b1c08)
#
# The margin SQL uses
#   SUM(quantity * COALESCE(items.cost_per_unit, products.cost_price))
# so:
#   - rows with a captured `cost_per_unit` lock in the cost-at-sale and
#     do NOT drift when Product.cost_price changes
#   - legacy rows (NULL) still render via the Product.cost_price fallback
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_margin_uses_captured_cost_per_unit_when_present(
    client: TestClient, admin_headers: dict, db: Session
):
    """A SalesOrderItem with cost_per_unit set ignores any later
    change to Product.cost_price — the whole point of the migration."""
    product = Product(
        name="Stable Cost", sku="STABLE-COST",
        cost_price=10.0,  # current master cost
        default_resale_price=50.0,
        is_bundle=False,
    )
    db.add(product)
    db.flush()
    order = SalesOrder(
        status="COMPLETED", total_price=200.0,
        created_at=datetime.utcnow() - timedelta(days=1),
        source=OrderSource.AMAZON, external_order_id="STABLE-1",
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        quantity=4, price_per_unit=50.0,
        cost_per_unit=4.0,  # snapshotted when the master cost was 4
    ))
    db.commit()

    # Simulate the buyer raising cost_price after the sale shipped.
    product.cost_price = 99.0
    db.commit()

    response = client.get(
        "/api/v1/reports/margin/export",
        params={"window_days": 30},
        headers=admin_headers,
    )
    rows = list(csv.reader(io.StringIO(response.text)))
    by_sku = {row[1]: row for row in rows[1:]}
    line = by_sku["STABLE-COST"]
    # revenue = 4 * 50 = 200
    # captured cost = 4 * 4 = 16  (NOT 4 * 99 = 396 from drifted master)
    # gross = 184; margin = 92%
    assert line[5] == "USD 200.00"
    assert line[6] == "USD 16.00"
    assert line[7] == "USD 184.00"
    assert line[8] == "92.0%"


@pytest.mark.db
def test_margin_falls_back_to_product_cost_for_legacy_rows(
    client: TestClient, admin_headers: dict, db: Session
):
    """A SalesOrderItem ingested before the migration has
    cost_per_unit=NULL. The COALESCE falls back to Product.cost_price
    so the report still renders — the only behaviour we keep from
    pre-migration."""
    product = Product(
        name="Legacy", sku="LEGACY-COST",
        cost_price=8.0,
        default_resale_price=20.0,
        is_bundle=False,
    )
    db.add(product)
    db.flush()
    order = SalesOrder(
        status="COMPLETED", total_price=40.0,
        created_at=datetime.utcnow() - timedelta(days=1),
        source=OrderSource.FULCRUM, external_order_id="LEGACY-1",
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        quantity=2, price_per_unit=20.0,
        cost_per_unit=None,  # legacy
    ))
    db.commit()

    response = client.get(
        "/api/v1/reports/margin/export",
        params={"window_days": 30},
        headers=admin_headers,
    )
    rows = list(csv.reader(io.StringIO(response.text)))
    by_sku = {row[1]: row for row in rows[1:]}
    line = by_sku["LEGACY-COST"]
    # revenue = 2 * 20 = 40; cost = 2 * 8 = 16; gross = 24; margin = 60%
    assert line[5] == "USD 40.00"
    assert line[6] == "USD 16.00"
    assert line[7] == "USD 24.00"
    assert line[8] == "60.0%"


@pytest.mark.db
def test_margin_mixes_captured_and_legacy_rows_for_same_product(
    client: TestClient, admin_headers: dict, db: Session
):
    """A product with both pre- and post-migration sales must sum
    correctly: captured rows use their captured cost; legacy rows fall
    back to Product.cost_price. Verifies the COALESCE is applied
    per-row (not per-product)."""
    product = Product(
        name="Mixed", sku="MIXED-COST",
        cost_price=10.0,
        default_resale_price=30.0,
        is_bundle=False,
    )
    db.add(product)
    db.flush()
    order = SalesOrder(
        status="COMPLETED", total_price=120.0,
        created_at=datetime.utcnow() - timedelta(days=1),
        source=OrderSource.FULCRUM, external_order_id="MIXED-1",
    )
    db.add(order)
    db.flush()
    # Legacy row (NULL captured cost → falls back to product.cost_price=10).
    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        quantity=2, price_per_unit=30.0, cost_per_unit=None,
    ))
    # Captured row (cost_per_unit=5, ignores product.cost_price).
    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        quantity=2, price_per_unit=30.0, cost_per_unit=5.0,
    ))
    db.commit()

    response = client.get(
        "/api/v1/reports/margin/export",
        params={"window_days": 30},
        headers=admin_headers,
    )
    rows = list(csv.reader(io.StringIO(response.text)))
    by_sku = {row[1]: row for row in rows[1:]}
    line = by_sku["MIXED-COST"]
    # units = 4; revenue = 4 * 30 = 120
    # cost = 2 * 10 (legacy) + 2 * 5 (captured) = 30
    # gross = 90; margin = 75%
    assert line[4] == "4"
    assert line[5] == "USD 120.00"
    assert line[6] == "USD 30.00"
    assert line[7] == "USD 90.00"
    assert line[8] == "75.0%"
