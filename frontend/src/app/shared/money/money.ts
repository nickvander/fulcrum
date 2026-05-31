/**
 * Shared MXN money formatter (single source of truth).
 *
 * Guardrail: money is ALWAYS MXN across Fulcrum and must flow through this one
 * formatter — no inline `currency:'USD'`, no bare `'$'` prefixes. Numbers render
 * tabular and right-aligned in tables (see .num cell styling).
 *
 * Mexico convention: es-MX locale, `$` symbol, comma thousands separator,
 * 2 decimals (e.g. `$1,234.50`). The ISO code can be appended for disambiguation
 * (e.g. `$1,234.50 MXN`).
 */

const MXN_FORMATTER = new Intl.NumberFormat('es-MX', {
  style: 'currency',
  currency: 'MXN',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const MXN_FORMATTER_NO_CENTS = new Intl.NumberFormat('es-MX', {
  style: 'currency',
  currency: 'MXN',
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

export interface MxnOptions {
  /** Drop the cents when the value is a whole number (compact display). */
  hideCents?: boolean;
  /** Append the ` MXN` ISO code for explicit disambiguation. */
  showCode?: boolean;
}

/**
 * Format a numeric amount as Mexican pesos.
 * Null / undefined / NaN collapse to a neutral dash so tables never print "$NaN".
 */
export function formatMxn(value: number | null | undefined, options: MxnOptions = {}): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '—';
  }
  const fmt = options.hideCents && Number.isInteger(value) ? MXN_FORMATTER_NO_CENTS : MXN_FORMATTER;
  const out = fmt.format(value);
  return options.showCode ? `${out} MXN` : out;
}
