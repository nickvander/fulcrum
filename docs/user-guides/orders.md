# User Guide: Orders

The **Orders** section lists sales orders ingested from your connected
marketplaces (MercadoLibre and Amazon) alongside any internal (`FULCRUM`)
orders. Clicking an order opens the **order-detail page**, which is the richest
view of a single order's economics and lifecycle.

## Accessing Orders

Click **Orders** in the left sidebar to see the order list, then click any order
to open its detail page.

## The Order-Detail Page

### Header

The header shows the order's channel (its `source`), order number, the date it
was placed, a status chip, and the order **total** rendered in the order's own
currency. When the order came from a marketplace, an **external reference**
card links out to the order on that channel.

### Economics (cost breakdown & net margin)

For orders with a cost breakdown, the **Economics** card walks from revenue down
to net profit:

```
revenue
  − cost of goods sold (COGS)
  − marketplace fees
  − shipping
  − ad spend        (shown only when non-zero)
  − other costs     (shown only when non-zero)
  = net profit  (+ net margin %)
```

A badge marks whether the fee figures are **settled** (reconciled from the
marketplace's settlement data) or **estimated** (computed from the channel's
default fee config). The net-margin percentage is color-coded so a thin or
negative margin stands out.

### MXN-equivalent (foreign-currency orders)

When an order is in a currency other than MXN, an **MXN-equivalent** line shows
the revenue converted to pesos, along with the exchange rate that was applied.
The conversion uses the FX rate that was true on the order's date (see
[Settings → Currency](settings.md#currency) for how rates are recorded). Amounts
throughout the page are rendered with a currency-tagged symbol (`MX$`, `US$`, …)
so pesos and dollars are never ambiguous.

### Line Items

A table lists each line item with the product (name + SKU, or an
**unmatched** marker when the marketplace SKU couldn't be matched to a local
product), quantity, unit price, subtotal, and per-line margin.

### Returns

The **Returns** section lists returns recorded against the order (when, by whom,
which product, how many units back, and an optional reason). Use **Record
return** to log a physical return; recording a return re-credits stock.

### Refund Events

For Amazon orders, any partial-refund events recorded against the order are
listed with their date, refund id, and amount.

### Status Timeline

The **Status timeline** shows every status transition the order has been
through — each entry shows the `from → to` status, when it changed, and the
signal that triggered it (e.g. `ml_webhook`, `ml_poll`, `amazon_poll`, or
`manual`). A reversed cost breakdown (e.g. after a cancellation or refund) is
flagged on the Economics card so the order drops out of current-period revenue
totals while staying queryable.

---

_Last Updated: May 2026_
