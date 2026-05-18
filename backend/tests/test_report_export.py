"""Unit tests for `src.services.report_export`.

The streamers are exercised end-to-end by the per-report endpoint tests
(test_low_stock_export.py, test_sales_summary_export.py,
test_inventory_snapshot_export.py). These tests focus on the shape /
contracts of the shared module itself so a future refactor (or a brand-
new report wiring into the same helpers) catches regressions early.
"""
import csv
import io

from src.services.report_export import (
    ReportColumn,
    ReportTable,
    fmt_currency,
    fmt_float,
    fmt_int,
    fmt_percent,
    render_csv,
    render_pdf,
    stream_csv,
)


# --- Formatters --------------------------------------------------------------


def test_fmt_int_handles_strings_floats_and_none():
    assert fmt_int(1234) == "1,234"
    assert fmt_int(1234.5) == "1,234"
    assert fmt_int("42") == "42"
    assert fmt_int(None) == ""
    assert fmt_int("") == ""
    assert fmt_int("not a number") == "not a number"  # passthrough on parse fail


def test_fmt_currency_strips_none_and_pads_decimals():
    assert fmt_currency(0) == "USD 0.00"
    assert fmt_currency(12.5) == "USD 12.50"
    assert fmt_currency(1234567.89) == "USD 1,234,567.89"
    assert fmt_currency(None) == ""
    assert fmt_currency(50, currency="MXN") == "MXN 50.00"


def test_fmt_float_factory_respects_decimals():
    two = fmt_float(2)
    one = fmt_float(1)
    assert two(3.14159) == "3.14"
    assert one(3.14159) == "3.1"
    assert two(None) == ""


def test_fmt_percent_appends_unit_and_handles_zero():
    assert fmt_percent(0) == "0.0%"
    assert fmt_percent(42.5) == "42.5%"
    assert fmt_percent(None) == ""


# --- CSV streamer ------------------------------------------------------------


def _read_csv_bytes(body: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(body.decode("utf-8"))))


def _example_table(rows=None) -> ReportTable:
    return ReportTable(
        title="Sample",
        filename_stem="sample-report",
        columns=[
            ReportColumn("sku",   "SKU"),
            ReportColumn("name",  "Product"),
            ReportColumn("price", "Price", align="right", formatter=fmt_currency),
        ],
        rows=rows if rows is not None else [
            {"sku": "A-1", "name": "Widget", "price": 19.99},
            {"sku": "B-2", "name": "Gadget", "price": None},
        ],
    )


def test_render_csv_uses_column_key_as_default_csv_header():
    """The PDF gets a human-friendly `header`; the CSV defaults to the
    snake-case `key` so machine-readable consumers don't have to deal with
    spaces. This is the core promise of the dual-header design."""
    rows = _read_csv_bytes(render_csv(_example_table()))
    assert rows[0] == ["sku", "name", "price"]
    assert rows[1] == ["A-1", "Widget", "USD 19.99"]
    assert rows[2] == ["B-2", "Gadget", ""]  # None formats to empty string


def test_render_csv_honors_csv_header_override():
    table = _example_table()
    table.columns[0] = ReportColumn("sku", "SKU", csv_header="Item Code")
    rows = _read_csv_bytes(render_csv(table))
    assert rows[0] == ["Item Code", "name", "price"]


def test_stream_csv_filename_is_date_stamped():
    import re
    response = stream_csv(_example_table())
    cd = response.headers["content-disposition"]
    assert re.search(r'filename="sample-report-\d{4}-\d{2}-\d{2}\.csv"', cd)


def test_render_csv_empty_rows_still_emits_header_only():
    rows = _read_csv_bytes(render_csv(_example_table(rows=[])))
    assert len(rows) == 1
    assert rows[0] == ["sku", "name", "price"]


def test_render_csv_supports_attribute_objects_not_just_dicts():
    """Real reports pass Pydantic models. The streamer must accept any
    object that responds to attribute access — not require dict rows."""
    class Row:
        def __init__(self, sku, name, price):
            self.sku, self.name, self.price = sku, name, price
    table = _example_table(rows=[Row("Z-9", "ObjWidget", 7.50)])
    rows = _read_csv_bytes(render_csv(table))
    assert rows[1] == ["Z-9", "ObjWidget", "USD 7.50"]


# --- PDF streamer ------------------------------------------------------------


def test_render_pdf_returns_a_valid_pdf_byte_string():
    body = render_pdf(_example_table())
    assert body.startswith(b"%PDF-")
    assert body.rstrip().endswith(b"%%EOF")


def test_render_pdf_row_style_does_not_explode_on_unknown_severity():
    """row_style is a soft contract: returning None for any row should not
    crash the streamer. This guards against bugs in caller code where
    enum-like severities grow new variants."""
    table = _example_table()
    table.row_style = lambda row: {"background": "#fde7e7"} if row["sku"] == "A-1" else None
    body = render_pdf(table)
    assert body.startswith(b"%PDF-")


def test_render_pdf_empty_rows_renders_empty_message():
    """An empty report should still render — accountants want a stamped
    'nothing to report' page, not a blank file."""
    body = render_pdf(_example_table(rows=[]))
    assert body.startswith(b"%PDF-")
    assert len(body) > 500  # not just an empty doc
