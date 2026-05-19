import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';


/**
 * JSON shapes from the Phase-8 Track-1/2 cost-rollup endpoints.
 * Numbers are MXN; per-channel rows preserve the marketplace's own
 * currency totals for future FX-aware widgets but v1 is MXN-only.
 */
export interface CostRollup {
  window_days: number;
  source?: string | null;
  orders: number;
  revenue_amount_mxn: number;
  cogs_amount: number;
  marketplace_fees_amount: number;
  shipping_cost_amount: number;
  ad_spend_amount: number;
  other_cost_amount: number;
  total_cost_amount: number;
  net_profit_amount: number;
  net_margin_percent: number | null;
}

export interface CostRollupByChannelRow extends CostRollup {
  source: string;
}

export interface CostRollupByChannelResponse {
  window_days: number;
  channels: CostRollupByChannelRow[];
}

export interface CostRollupDailyRow {
  date: string; // ISO YYYY-MM-DD
  orders: number;
  revenue_amount_mxn: number;
  total_cost_amount: number;
  net_profit_amount: number;
}

export interface CostRollupDailyResponse {
  window_days: number;
  series: CostRollupDailyRow[];
}

export interface TopMoverRow {
  product_id: number;
  name: string | null;
  sku: string | null;
  units: number;
  revenue_amount: number;
  cogs_amount: number;
  overhead_amount: number;
  total_cost_amount: number;
  net_profit_amount: number;
  net_margin_percent: number | null;
}

export interface TopMoversResponse {
  window_days: number;
  limit: number;
  rows: TopMoverRow[];
}

export interface DeadStockRow {
  product_id: number;
  product_name: string;
  product_sku: string | null;
  on_hand: number;
  units_sold: number;
  daily_velocity: number;
  /**
   * Calendar days since the product's most-recent realized sale.
   * `null` when the product has NEVER sold — UI sorts those to the
   * top because never-sold inventory is the worst kind.
   */
  days_since_last_sale: number | null;
  cost_price: number | null;
  /** on_hand × cost_price; the dollars "frozen" in this SKU. */
  stock_value_at_cost: number | null;
}

export interface DeadStockResponse {
  window_days: number;
  threshold_daily_velocity: number;
  rows: DeadStockRow[];
}

/**
 * CSV/PDF download endpoints for the velocity / margin / stockout
 * reports. These reports do not have a JSON shape on the frontend yet —
 * the dashboard widget only triggers blob downloads, and the backend
 * report_export helper handles content-type + filename headers.
 *
 * Default `limit` is 2000 to match the backend (the "give me
 * everything" use case for spreadsheet triage). Window/imminent/watch
 * defaults are mirrored from the backend Query defaults so a caller
 * that just wants "now" can pass no arguments.
 */
@Injectable({ providedIn: 'root' })
export class AnalyticsReportsService {
  private apiUrl = `${environment.apiUrl}/reports`;

  constructor(private http: HttpClient) {}

  exportVelocityCsv(windowDays = 30, limit = 2000): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/velocity/export`, { window_days: windowDays, limit });
  }

  exportVelocityPdf(windowDays = 30, limit = 2000): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/velocity/export-pdf`, { window_days: windowDays, limit });
  }

  exportMarginCsv(windowDays = 30, limit = 2000): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/margin/export`, { window_days: windowDays, limit });
  }

  exportMarginPdf(windowDays = 30, limit = 2000): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/margin/export-pdf`, { window_days: windowDays, limit });
  }

  exportStockoutCsv(
    windowDays = 30,
    imminentDays = 7,
    watchDays = 14,
    limit = 2000,
  ): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/stockout/export`, {
      window_days: windowDays,
      imminent_days: imminentDays,
      watch_days: watchDays,
      limit,
    });
  }

  exportStockoutPdf(
    windowDays = 30,
    imminentDays = 7,
    watchDays = 14,
    limit = 2000,
  ): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/stockout/export-pdf`, {
      window_days: windowDays,
      imminent_days: imminentDays,
      watch_days: watchDays,
      limit,
    });
  }

  private blobGet(url: string, params: Record<string, number>): Observable<Blob> {
    let httpParams = new HttpParams();
    for (const [k, v] of Object.entries(params)) {
      httpParams = httpParams.set(k, String(v));
    }
    return this.http.get(url, { params: httpParams, responseType: 'blob' });
  }

  // -- Phase 8 Track 1/2: cost rollup + dashboard widgets ------------

  /**
   * Aggregate net-margin rollup over a window. Powers the
   * "Today's profit" ticker (window_days=1) and any other single-
   * number net-margin display.
   */
  costRollup(windowDays = 30, source?: string): Observable<CostRollup> {
    let params = new HttpParams().set('window_days', String(windowDays));
    if (source) params = params.set('source', source);
    return this.http.get<CostRollup>(`${this.apiUrl}/cost-rollup`, { params });
  }

  /**
   * Per-channel rollup. Powers the "Margin by channel" stacked-bar
   * chart — one stack per source showing the COGS / fees / shipping /
   * profit breakdown.
   */
  costRollupByChannel(windowDays = 30): Observable<CostRollupByChannelResponse> {
    const params = new HttpParams().set('window_days', String(windowDays));
    return this.http.get<CostRollupByChannelResponse>(
      `${this.apiUrl}/cost-rollup/by-channel`, { params },
    );
  }

  /**
   * Daily time-series. Powers the "Sales vs spend" line chart.
   * Includes zero-rows for quiet days so the chart's x-axis stays
   * continuous.
   */
  costRollupDaily(windowDays = 30): Observable<CostRollupDailyResponse> {
    const params = new HttpParams().set('window_days', String(windowDays));
    return this.http.get<CostRollupDailyResponse>(
      `${this.apiUrl}/cost-rollup/daily`, { params },
    );
  }

  /**
   * Top N products by revenue. Powers the "Top movers" table.
   * Per-product net profit includes a pro-rated share of the
   * order-level fees + shipping, computed server-side.
   */
  topMovers(windowDays = 30, limit = 10): Observable<TopMoversResponse> {
    const params = new HttpParams()
      .set('window_days', String(windowDays))
      .set('limit', String(limit));
    return this.http.get<TopMoversResponse>(
      `${this.apiUrl}/top-movers`, { params },
    );
  }

  /**
   * Products with on-hand stock but near-zero recent sales velocity.
   * Powers the dashboard "Dead stock" widget. Threshold is in
   * units/day; the backend default 0.1 (~< 1 sale per 10 days) is
   * passed explicitly here so frontend + backend stay in sync.
   */
  deadStock(
    windowDays = 30, thresholdDailyVelocity = 0.1, limit = 20,
  ): Observable<DeadStockResponse> {
    const params = new HttpParams()
      .set('window_days', String(windowDays))
      .set('threshold_daily_velocity', String(thresholdDailyVelocity))
      .set('limit', String(limit));
    return this.http.get<DeadStockResponse>(
      `${this.apiUrl}/dead-stock`, { params },
    );
  }
}
