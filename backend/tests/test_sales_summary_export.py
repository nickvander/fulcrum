"""CSV + PDF export for the sales-by-channel summary."""
import csv
import io
import re
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.order import OrderSource, SalesOrder


def _seed_order(db: Session, *, source: OrderSource, total: float, external_id: str) -> None:
    db.add(
        SalesOrder(
            status="COMPLETED",
            total_price=total,
            created_at=datetime.utcnow(),
            source=source,
            external_order_id=external_id,
        )
    )


@pytest.mark.db
def test_summary_csv_returns_one_row_per_channel_with_share_column(
    client: TestClient, admin_headers: dict, db: Session
):
    _seed_order(db, source=OrderSource.MERCADOLIBRE, total=300.0, external_id="ML-1")
    _seed_order(db, source=OrderSource.AMAZON,       total=100.0, external_id="AMZ-1")
    db.commit()

    response = client.get("/api/v1/sales-orders/summary/export", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    cd = response.headers["content-disposition"]
    assert re.search(r'filename="fulcrum-sales-by-channel-\d{4}-\d{2}-\d{2}\.csv"', cd)

    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == ["channel", "orders", "revenue", "share"]
    by_channel = {row[0]: row for row in rows[1:]}

    assert "MercadoLibre" in by_channel
    assert "Amazon" in by_channel
    # MercadoLibre is $300 / $400 = 75% of total revenue
    assert by_channel["MercadoLibre"][1] == "1"
    assert by_channel["MercadoLibre"][2] == "USD 300.00"
    assert by_channel["MercadoLibre"][3] == "75.0%"
    assert by_channel["Amazon"][3] == "25.0%"


@pytest.mark.db
def test_summary_csv_empty_window_still_returns_header_only(
    client: TestClient, admin_headers: dict, db: Session
):
    """No orders → 200 with the header row and every known channel emitted
    at zero. Empty windows aren't an error."""
    response = client.get(
        "/api/v1/sales-orders/summary/export",
        params={"days": 1},
        headers=admin_headers,
    )
    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.text)))
    # Header + 3 known channels (MercadoLibre, Amazon, Fulcrum) at 0
    assert rows[0] == ["channel", "orders", "revenue", "share"]
    body_rows = rows[1:]
    assert len(body_rows) == 3
    for row in body_rows:
        assert row[1] == "0"
        assert row[2] == "USD 0.00"
        assert row[3] == "0.0%"


@pytest.mark.db
def test_summary_pdf_returns_valid_pdf(
    client: TestClient, admin_headers: dict, db: Session
):
    _seed_order(db, source=OrderSource.MERCADOLIBRE, total=50.0, external_id="ML-PDF-1")
    db.commit()

    response = client.get("/api/v1/sales-orders/summary/export-pdf", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    body = response.content
    assert body.startswith(b"%PDF-")
    assert body.rstrip().endswith(b"%%EOF")
    cd = response.headers["content-disposition"]
    assert re.search(r'filename="fulcrum-sales-by-channel-\d{4}-\d{2}-\d{2}\.pdf"', cd)
