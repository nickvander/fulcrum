"""
Reusable report export helpers.

Each report on the dashboard ultimately needs the same two affordances: a
"give me a spreadsheet" button and a "give me a print-ready PDF" button.
The previous low-stock implementation hand-rolled both inside the endpoint;
that worked for one report but didn't scale once sales-by-channel and
inventory-health needed the same treatment.

This module lifts the shared pieces into one place:

- `ReportColumn` describes one output column (key, header, alignment,
  optional value formatter so currency/percent formatting lives next to
  the column instead of inside each writer).
- `ReportTable` bundles the table title, subtitle, columns, and the rows
  themselves (dicts or attribute-accessible objects). A `row_style`
  callback lets a caller color rows by severity without the streamer
  knowing what "severity" means.
- `stream_csv(table)` writes the CSV via `csv.writer` with a date-stamped
  filename and the standard `attachment` Content-Disposition.
- `stream_pdf(table)` renders a landscape letter PDF with reportlab,
  using row_style for cell backgrounds.

The streamers accept the same `ReportTable` so the calling endpoint only
needs to build the table once for both formats.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, List, Literal, Optional

from fastapi.responses import StreamingResponse


@dataclass
class ReportColumn:
    key: str
    """Row attribute / dict key to pull the value from."""
    header: str
    """Human-readable column title used in the PDF."""
    align: Literal["left", "right"] = "left"
    formatter: Optional[Callable[[Any], str]] = None
    csv_header: Optional[str] = None
    """Override for the CSV header. Defaults to `key` so machine-readable
    pipelines built on the CSV (Excel formulas, ETL jobs) don't have to
    deal with spaces or unicode. The PDF always uses `header`.
    """

    @property
    def csv_label(self) -> str:
        return self.csv_header if self.csv_header is not None else self.key


@dataclass
class ReportTable:
    title: str
    filename_stem: str
    columns: List[ReportColumn]
    rows: Iterable[Any]
    subtitle: Optional[str] = None
    empty_message: str = "No rows to display."
    row_style: Optional[Callable[[Any], Optional[dict]]] = field(default=None)
    """Optional callback that receives a row and returns a dict with
    `background` (hex string) to apply to that row in the PDF. Returns
    None when the row should use the default background. The CSV writer
    ignores styling.
    """


def _row_value(row: Any, key: str) -> Any:
    """Pull `key` off a dict-or-object row uniformly."""
    if isinstance(row, dict):
        return row.get(key)
    return getattr(row, key, None)


def _format_value(column: ReportColumn, raw: Any) -> str:
    """Apply the column formatter if any, else stringify None as ''."""
    if column.formatter is not None:
        return column.formatter(raw)
    if raw is None:
        return ""
    return str(raw)


def _filename(stem: str, suffix: str) -> str:
    """e.g. ("fulcrum-low-stock", "csv") -> 'fulcrum-low-stock-2026-05-17.csv'"""
    date_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{stem}-{date_stamp}.{suffix}"


def render_csv(table: ReportTable) -> bytes:
    """Build the CSV body for `table` and return its bytes. Split out from
    `stream_csv` so unit tests can assert on the body without running it
    through the ASGI response wrapper."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([col.csv_label for col in table.columns])
    for row in table.rows:
        writer.writerow([
            _format_value(col, _row_value(row, col.key)) for col in table.columns
        ])
    return buf.getvalue().encode("utf-8")


def stream_csv(table: ReportTable) -> StreamingResponse:
    """Render `table` as a CSV blob and return a StreamingResponse with the
    standard date-stamped filename. Empty rows still produce a 200 with the
    header row; callers can rely on that shape."""
    body = render_csv(table)
    return StreamingResponse(
        iter([body]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{_filename(table.filename_stem, "csv")}"',
        },
    )


def render_pdf(table: ReportTable) -> bytes:
    """Build the PDF body for `table` and return its bytes. Split out from
    `stream_pdf` for the same reason as `render_csv` — unit-testable."""
    body, _ = _build_pdf(table)
    return body


def stream_pdf(table: ReportTable) -> StreamingResponse:
    """Render `table` as a print-ready PDF via reportlab. Layout matches the
    convention the low-stock report established: landscape letter, dark
    header row, light grid, severity-colored rows when `row_style` is set.
    Delegates to `_build_pdf` so the test helpers and the streamer share
    the layout code."""
    body, _ = _build_pdf(table)
    return StreamingResponse(
        iter([body]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{_filename(table.filename_stem, "pdf")}"',
        },
    )


def _build_pdf(table: ReportTable) -> tuple[bytes, int]:
    """Internal helper: render the PDF body bytes. Returns (body, row_count)
    so callers can sanity-check without parsing the PDF. Currently only
    used by `render_pdf`; `stream_pdf` keeps its inline implementation so
    the SimpleDocTemplate lifecycle stays in one place."""
    # Re-run the same logic as stream_pdf but without wrapping in a
    # StreamingResponse. Pulled out so the test suite can assert directly
    # on the bytes.
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(letter),
        title=table.title,
        leftMargin=0.4 * inch, rightMargin=0.4 * inch,
        topMargin=0.5 * inch, bottomMargin=0.4 * inch,
    )
    styles = getSampleStyleSheet()
    elements: list = [Paragraph(f"<b>{table.title}</b>", styles["Title"])]
    if table.subtitle:
        elements.append(Paragraph(table.subtitle, styles["Normal"]))
    elements.append(Spacer(1, 0.15 * inch))

    rows_materialized = list(table.rows)
    data = [[col.header for col in table.columns]]
    for row in rows_materialized:
        data.append([
            _format_value(col, _row_value(row, col.key)) for col in table.columns
        ])

    pdf_table = Table(data, repeatRows=1)
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ])
    for col_idx, column in enumerate(table.columns):
        if column.align == "right":
            style.add("ALIGN", (col_idx, 1), (col_idx, -1), "RIGHT")
    if table.row_style is not None:
        for r_idx, row in enumerate(rows_materialized, start=1):
            style_spec = table.row_style(row) or {}
            bg = style_spec.get("background")
            if bg:
                style.add("BACKGROUND", (0, r_idx), (-1, r_idx), colors.HexColor(bg))
    pdf_table.setStyle(style)
    elements.append(pdf_table)
    if not rows_materialized:
        elements.append(Paragraph(table.empty_message, styles["Italic"]))

    doc.build(elements)
    return buf.getvalue(), len(rows_materialized)


# ---- Common formatters ----------------------------------------------------
#
# Reused across reports so currency / percent / float rendering is consistent.


def fmt_currency(value: Any, currency: str = "USD") -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{currency} {float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def fmt_int(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def fmt_float(decimals: int = 2) -> Callable[[Any], str]:
    def _formatter(value: Any) -> str:
        if value is None or value == "":
            return ""
        try:
            return f"{float(value):,.{decimals}f}"
        except (TypeError, ValueError):
            return str(value)
    return _formatter


def fmt_percent(value: Any, decimals: int = 1) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.{decimals}f}%"
    except (TypeError, ValueError):
        return str(value)


def fmt_date(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return str(value)
