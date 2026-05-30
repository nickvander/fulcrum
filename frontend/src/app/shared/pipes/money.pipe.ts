import { Pipe, PipeTransform } from '@angular/core';

/**
 * Consistent money formatting across the app.
 *
 * Why this exists: money was rendered ad-hoc — the dashboard showed
 * `MX$525` while the product list / order detail showed a bare `$329.00`,
 * which is ambiguous for a Mexican operator who also sources in USD.
 * This pipe gives every amount an unambiguous currency-tagged symbol
 * driven by the record's own currency code.
 *
 *   {{ 1234.5 | money }}            → "MX$1,234.50"   (defaults to MXN)
 *   {{ 50 | money:'USD' }}          → "US$50.00"
 *   {{ amount | money:product.currency }}
 *   {{ null | money }}              → "—"
 *
 * Symbols are an explicit, controlled map (not locale-derived) so the
 * peso and dollar never both collapse to a bare "$" depending on the
 * active locale — MX$ vs US$ is always distinguishable.
 */
@Pipe({ name: 'money', standalone: true })
export class MoneyPipe implements PipeTransform {
  private static readonly SYMBOLS: Record<string, string> = {
    MXN: 'MX$',
    USD: 'US$',
    EUR: '€',
    GBP: '£',
    CAD: 'CA$',
    BRL: 'R$',
    JPY: '¥',
    CNY: 'CN¥',
  };

  transform(
    amount: number | null | undefined,
    currency: string | null | undefined = 'MXN',
    options?: { showCode?: boolean },
  ): string {
    if (amount === null || amount === undefined || Number.isNaN(amount)) {
      return '—';
    }
    const code = (currency || 'MXN').toUpperCase();
    const symbol = MoneyPipe.SYMBOLS[code];

    // JPY conventionally has no decimal places; everything else gets 2.
    const fractionDigits = code === 'JPY' ? 0 : 2;
    const num = new Intl.NumberFormat('en-US', {
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits,
    }).format(amount);

    if (!symbol) {
      // Unknown code → render the code after the number, e.g. "50.00 AUD".
      return `${num} ${code}`;
    }
    const formatted = `${symbol}${num}`;
    return options?.showCode ? `${formatted} ${code}` : formatted;
  }
}
