import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface ExchangeRate {
  id: number;
  base_currency: string;
  quote_currency: string;
  rate: number;
  rate_date: string;
  source: string;
}

export interface ExchangeRateCreate {
  base_currency: string;
  quote_currency: string;
  rate: number;
  /** ISO date (YYYY-MM-DD). Omit to default to today on the server. */
  rate_date?: string | null;
  source?: string;
}

/**
 * Talks to the `/currency` API: list + record FX rates.
 *
 * Recorded rates feed historical money conversions (e.g. normalising a
 * USD order's revenue to MXN at the rate that was true on the order
 * date). The operator-facing admin screen lives under Settings.
 */
@Injectable({ providedIn: 'root' })
export class CurrencyService {
  private apiUrl = `${environment.apiUrl}/currency`;

  constructor(private http: HttpClient) {}

  /** List recorded rates, newest first. Optionally filter by pair. */
  listRates(opts: { base?: string; quote?: string; limit?: number } = {}): Observable<ExchangeRate[]> {
    let params = new HttpParams();
    if (opts.base) params = params.set('base_currency', opts.base);
    if (opts.quote) params = params.set('quote_currency', opts.quote);
    if (opts.limit != null) params = params.set('limit', String(opts.limit));
    return this.http.get<ExchangeRate[]>(`${this.apiUrl}/rates`, { params });
  }

  /** Record (or upsert) a rate. Admin-only on the server. */
  recordRate(payload: ExchangeRateCreate): Observable<ExchangeRate> {
    return this.http.post<ExchangeRate>(`${this.apiUrl}/rates`, payload);
  }
}
