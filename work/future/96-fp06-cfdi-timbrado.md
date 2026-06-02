# 96 — FP-06: CFDI 4.0 timbrado (live stamping) in Fulcrum

> **Origin:** Follow-up to B7 (CFDI export-only, shipped 2026-06-01). Vendio's
> `ADR-018` + `concepts/architecture.md` designate **Fulcrum as the stamper**
> ("Fulcrum owns the order, so it stamps", FP-06). This doc scopes the live
> PAC integration that turns the B7 export into legally-valid, stamped CFDIs.
>
> **Status:** scoped, not started. **Launch-blocking for Vendio** (legal —
> can't sell in MX without CFDI). **`[HIL]` on every diff** (fiscal + handles
> the CSD private key). Needs Facturama **sandbox** credentials + a test CSD
> to build end-to-end.

## What B7 already gives us (the foundation)

- `services/cfdi_service.read_issuer_config` / `save_issuer_config` — emisor
  identity (RFC / razón social / régimen / CP / default SAT keys / IVA) in
  `StoreSettings.settings['cfdi']`.
- `build_cfdi_report` — realized sales in CFDI-ready shape (conceptos, IVA
  backed out of tax-inclusive prices, document-consistent totals) issued to the
  RFC genérico (público en general).
- `GET /reports/cfdi` + CSV export; Settings → CFDI tab.

FP-06 adds: a **PAC adapter**, **persistence of the stamped document**
(UUID/XML/PDF), **per-order receiver capture**, **cancellations + nota de
crédito**, the **factura global** job, and a **channel-aware invoicing policy**.

## Decision 1 — who invoices, per channel (avoids double-invoicing)

`SalesOrder` gets an `invoicing_source` derived from the channel + config:

| Channel | Default `invoicing_source` | Fulcrum behavior |
|---|---|---|
| **Storefront** (vendio, `source` = storefront) | `self` | Fulcrum stamps via PAC. |
| **Amazon** | `self` | Amazon doesn't issue buyer CFDI for the seller → Fulcrum stamps. |
| **MercadoLibre** | **configurable** (`self` \| `marketplace_handled`) | If you enrolled ML "facturación automática" (gave ML your CSD), ML stamps → Fulcrum **links/imports** ML's UUID, does **not** stamp. Otherwise Fulcrum stamps (specific RFC on request + monthly global). |

A per-channel setting (`cfdi.invoicing_policy[source]`) drives this. Stamping
endpoints **refuse** to stamp an order whose source is `marketplace_handled`
(returns a clear error), and a separate import path records the externally
issued UUID. This is the safeguard against issuing two CFDIs for one sale.

## Decision 2 — Fulcrum is the only PAC/CSD holder

Per ADR-018, **Vendio must not call the PAC directly.** Vendio's
`InvoicingProvider` (`packages/invoicing`) should **forward to a Fulcrum
endpoint**, not embed the PAC SDK. The CSD private key + PAC API key live in
Fulcrum **only**. (Today vendio's `pac.ts` stub looks like it would call the PAC
itself — reconcile that as part of this work so the cert lives in one place.)

## Data model (migration)

New table `cfdi_documents` (one row per issued/linked CFDI; an order can have a
factura + later a nota de crédito):

- `id`, `order_id` (FK, nullable for factura global which spans many orders),
  `kind` (`ingreso` | `egreso`/nota_credito | `global`),
- `uuid` (folio fiscal, unique), `status` (`stamped` | `cancelled` |
  `pending` | `error`), `invoicing_source` (`self` | `marketplace_handled`),
- `receiver_rfc`, `receiver_name`, `receiver_postal_code`, `receiver_regime`,
  `cfdi_use`, `subtotal_cents`, `iva_cents`, `total_cents`, `currency`,
- `xml_path` / `pdf_path` (or blob refs), `pac_vendor`, `stamped_at`,
  `cancelled_at`, `cancel_reason`, `related_uuid` (nota de crédito → original),
  `error_detail`.

Receiver capture (specific-RFC path): nullable CFDI receiver columns on
`SalesOrder` (or a small `sales_order_billing` row) set by the storefront at
checkout / by an operator on order detail. Absent → público-general.

> RFC + fiscal data is **PII**: never log raw; encrypt the CSD key at rest
> (reuse `core/encryption`); amounts in **centavos** end-to-end on the PAC path.

## Provider interface + Facturama adapter

`services/invoicing/base.py`:

```python
class InvoicingProvider(Protocol):
    def stamp(self, doc: CfdiStampRequest) -> CfdiStampResult: ...
    def cancel(self, uuid: str, reason: str) -> CfdiCancelResult: ...
    def nota_de_credito(self, original_uuid: str, amount_cents: int) -> CfdiStampResult: ...
    def factura_global(self, start: date, end: date) -> CfdiStampResult: ...
```

`services/invoicing/facturama.py` — the OD-04 default. Facturama accepts a JSON
CFDI payload and returns the stamped XML + PDF + UUID, so we **don't hand-author
XML**. Config: `pac_vendor`, `pac_api_key` (encrypted), `sandbox: bool`, CSD
upload. Finkok is a later alternative behind the same interface.

Build the payload by reusing B7's `build_cfdi_report` per-order logic (concepts,
IVA, totals) — refactor it so a single order can be turned into one stamp
request (DRY with the report).

## Endpoints (all `[HIL]`, admin-only)

- `POST /reports/cfdi/{order_id}/stamp` → builds payload, calls PAC, persists
  `cfdi_documents` row, returns UUID + PDF link. Idempotent: re-stamping a
  `stamped` order returns the existing UUID; refuses `marketplace_handled`.
- `POST /reports/cfdi/{uuid}/cancel` (reason code) → PAC cancel + status update.
- `POST /reports/cfdi/{uuid}/nota-credito` → egreso linked to the original.
- `POST /reports/cfdi/global` (start, end) → one factura global for the window's
  un-invoiced público-general `self` sales (Celery job for the monthly run).
- `POST /reports/cfdi/{order_id}/link-external` → record an ML-issued UUID for
  `marketplace_handled` orders (keeps the books complete without stamping).
- `GET /reports/cfdi/{order_id}/pdf` → fetch the stored PDF.

Hook order status → optional auto-stamp on a configurable trigger (e.g. order
reaches `COMPLETED`), gated by `invoicing_policy`.

## Vendio integration contract

Vendio (FP-06 on its side): capture RFC/régimen/uso at checkout → on order
create (already via the storefront BFF order-create path) pass the fiscal
fields → vendio's `InvoicingProvider.stamp()` **calls Fulcrum's
`/reports/cfdi/{order_id}/stamp`** (or Fulcrum auto-stamps storefront orders on
status). No PAC SDK or CSD in vendio.

## Secrets / config

- Settings → CFDI tab gains: PAC vendor + API key (encrypted, write-only),
  sandbox toggle, **CSD upload** (cer + key + key password, encrypted).
- Env fallback for the PAC key (`PAC_API_KEY`) like other secrets.

## Phasing

1. **P1 — schema + provider interface + `stamp` happy path** — ✅ **SHIPPED
   2026-06-01 (mock-tested).** Migration `b7e1c0d4f206` (`cfdi_documents` +
   per-order receiver columns); `CfdiDocument` model; `InvoicingProvider`
   interface (`services/invoicing/`) with a `FacturamaInvoicingProvider`
   (httpx, sandbox) + a deterministic `MockInvoicingProvider`;
   `cfdi_stamp_service` (per-channel policy resolution, per-order stamp-request
   build reusing B7's IVA back-out, idempotent `stamp_order`, `link_external`);
   endpoints `POST /reports/cfdi/{order_id}/stamp` (409 on marketplace_handled),
   `POST .../link-external`, `GET .../document`; CFDI config extended with
   `invoicing_policy` + encrypted PAC key. 11 tests via the mock PAC.
   **Open:** verify `FacturamaInvoicingProvider` against a live **sandbox**
   (field names in `_payload` are unconfirmed) once credentials exist; CSD
   upload; a frontend per-order Stamp/Link action on the order detail page.
2. **P2 — cancellations + nota de crédito + factura global job.**
3. **P3 — channel-aware policy + ML `link-external` import path + auto-stamp
   trigger + the vendio forwarding contract.**
4. **P4 — production CSD onboarding, monitoring, ret(timbre) accounting.**

## Open questions for the operator

- Are you enrolling in **ML "facturación automática"** (ML stamps ML orders) or
  self-issuing for ML? → sets the ML `invoicing_policy` default.
- Do you self-issue per-buyer facturas for marketplace sales on request, or only
  the monthly **factura global de público en general**?
- Facturama vs Finkok; do you already have a **CSD** + which **régimen fiscal**?
