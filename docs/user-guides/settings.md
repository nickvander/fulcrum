# User Guide: Settings

The **Settings** page provides configuration options for your Fulcrum instance,
organized into six tabs across the top of the page.

## Accessing Settings

Click **Settings** in the left sidebar. The page opens on a tabbed view; switch
between tabs to reach each configuration area.

## Settings Sections

The Settings page has six tabs: **AI Agents**, **Integrations**, **Marketing**,
**Inventory**, **Currency**, and **Data**.

### AI Agents

Choose the AI provider that powers Fulcrum's content-generation features (e.g.
product and listing descriptions) and store its API key. Only the active
provider needs a key configured; keys for the other providers can be saved for
later. The AI buttons elsewhere in the app stay disabled until a provider key is
present.

### Integrations

Manage how external systems talk to Fulcrum:

- **External API Keys**: Generate and revoke API keys used by integrations such
  as the Google Sheets sync. A newly generated key is shown once — copy it
  immediately.
- **Pending Sync**: Review imported changes (e.g. from Google Sheets) that are
  awaiting approval before they're applied.
- **Change Log**: Open the audit trail of who changed what, and from where.

> **Note**: Marketplace **App Credentials** (Client ID / Secret) are entered
> when you connect an account from the **Marketplaces** page, not here. Tokens
> are encrypted at rest using AES-256-GCM. See the
> [Marketplaces guide](marketplaces.md) for the connect flow.

### Marketing

Configure store and outbound-marketing settings:

- **Store Brand**: Store name and domain used in generated marketing assets.
- **Email Configuration**: The email provider/SMTP settings used to send
  notifications and campaign email.
- **Social Media**: Connect the social channels used by the marketing module.

### Inventory

Configure global defaults for inventory alerts:

- **Low Stock Days / Low Quantity Threshold**: The defaults that determine when
  a product is flagged as "Low Stock" on the dashboard and in alerts.
  - _Note_: These can be overridden on a per-product basis (reorder point /
    reorder quantity) in the Product Edit page.

### Currency

Record and review the foreign-exchange (FX) rates Fulcrum uses to normalize
foreign-currency revenue to MXN.

- **Record a rate**: Enter a **base** and **quote** currency, the **rate**
  (1 unit of base = _rate_ units of quote, e.g. `USD → MXN = 17.10`), and the
  **date** the rate applies to. Re-recording the same currency pair on the same
  date updates the existing entry.
- **Recorded rates**: The list shows previously recorded rates, newest first.

These rates power **historical** conversions: when a marketplace order arrives
in a currency other than MXN, its revenue is converted to MXN using the rate
that was true **on the order's date** — not today's rate. Conversions pick the
most-recent rate on or before that date; if no rate is on file, the figure falls
back to an unconverted estimate. (Backed by `GET` / `POST /api/v1/currency/rates`.)

### Data

Export and import platform data:

- **Export Data**: Download products and other entities as CSV or JSON.
- **Import Data**: Bring data into Fulcrum (e.g. bulk product import). Imports
  that need review surface under **Integrations → Pending Sync**.

> **Locale**: Language and theme are switched from the **General** tab's
> selectors, and the active locale can also be set from any URL via the
> `?lang=es-MX` (or `?lang=en`) query parameter, which is persisted for next
> time. Supported locales are English (`en`) and Spanish – Mexico (`es-MX`).

## Security Best Practices

- **Use Strong Passwords**: At least 12 characters with mixed case, numbers, and
  symbols.
- **Rotate Marketplace Credentials**: Periodically regenerate and update your
  Client Secrets.
- **Limit Admin Access**: Only give Admin roles to trusted team members.

---

_Last Updated: December 2025_
