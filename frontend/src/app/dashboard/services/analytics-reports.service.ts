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

/**
 * "¿Gané o perdí?" profit-summary shape. The business bottom line for a
 * period — order-contribution profit MINUS operating expenses — computed
 * server-side so the subtraction and window alignment live in one place.
 */
export type ProfitPeriod = 'this_month' | 'last_7d' | 'last_30d';
export type ProfitVerdict = 'won' | 'lost' | 'even';

export interface ProfitSummary {
  period: ProfitPeriod;
  start: string; // ISO date
  end: string;   // ISO date
  window_days: number;
  revenue_amount_mxn: number;
  sales_costs_amount: number;
  contribution_profit_amount: number;
  operating_expenses_amount: number;
  bottom_line_amount: number;
  net_margin_percent: number | null;
  orders: number;
  has_realized_orders: boolean;
  /** null when there are no realized orders → UI shows the empty state. */
  verdict: ProfitVerdict | null;
  double_count_warning: boolean;
  excluded_categories: string[];
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

export interface RefundsByChannelRow {
  /** One of 'FULCRUM' | 'MERCADOLIBRE' | 'AMAZON' for per-channel
   *  rows, or 'ALL' for the totals row. */
  source: string;
  refunds_count: number;
  refunded_amount_mxn: number;
  realized_orders_count: number;
  /** refunds_count / realized_orders_count × 100, rounded to 2dp.
   *  `null` when the window has zero realized orders (avoids
   *  misleading "0%" / "—" interpretations). */
  refund_rate_percent: number | null;
}

export interface RefundsSummaryResponse {
  /** Subtitle-style label mirrors the velocity/margin/stockout
   *  endpoints' label so widgets can reuse the same wording
   *  ('window 30d' vs. '2026-01-01 → 2026-03-31'). */
  window_label: string;
  totals: RefundsByChannelRow;
  by_channel: RefundsByChannelRow[];
}

export interface RefundsListRow {
  /** Discriminator: `order_cancelled` rows came from a status
   *  transition out of the realized set; `amazon_partial` rows came
   *  from the `amazon_order_refunds` table (Amazon-specific
   *  partial-refund events that don't flip the top-level status). */
  refund_kind: 'order_cancelled' | 'amazon_partial';
  order_id: number;
  source: string;
  external_order_id: string | null;
  /** ISO 8601 timestamp — transition `changed_at` for full refunds,
   *  SP-API `PostedDate` for Amazon partials. */
  refunded_at: string;
  refunded_amount_mxn: number;
  /** The order's status as of this row. Lets the UI distinguish a
   *  `CANCELLED` order from a `SHIPPED` order that took a partial
   *  refund. */
  order_status: string | null;
}

export interface RefundsListResponse {
  window_label: string;
  items: RefundsListRow[];
  total: number;
}

export interface ReturnsListRow {
  return_id: number;
  /** ISO 8601 timestamp from `sales_order_returns.received_at`. */
  received_at: string;
  order_id: number;
  external_order_id: string | null;
  /** Channel code: 'MERCADOLIBRE' | 'AMAZON' | 'FULCRUM' | null. */
  source: string | null;
  product_id: number | null;
  product_sku: string | null;
  product_name: string | null;
  quantity: number;
  reason: string | null;
  notes: string | null;
  recorded_by_email: string | null;
  /** `product.cost_price × quantity`, rounded. Lets the UI surface
   *  where the cost-of-returns concentrates. */
  value_at_cost: number;
}

export interface ReturnsListResponse {
  window_label: string;
  items: ReturnsListRow[];
  total: number;
}

export interface ReturnsByChannelRow {
  /** Channel code: 'FULCRUM' | 'MERCADOLIBRE' | 'AMAZON' | 'UNKNOWN'
   *  for per-channel rows; 'ALL' for the totals row. */
  source: string;
  returns_count: number;
  units_returned: number;
  /** Capital that came back, computed as units × current product
   *  cost_price (not retail). The dashboard signal is "how much
   *  inventory value is now in the returns pile"; cost basis is
   *  what the operator can actually recover or write off. */
  value_at_cost_mxn: number;
}

export interface ReturnsSummaryResponse {
  window_label: string;
  totals: ReturnsByChannelRow;
  by_channel: ReturnsByChannelRow[];
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
/**
 * Optional explicit calendar range. When both `startDate` and
 * `endDate` are set the backend pins the report to that range and
 * ignores `windowDays`. Set either alone and the missing bound is
 * filled in (`endDate` → now, `startDate` → end - windowDays). The
 * values should be ISO YYYY-MM-DD strings — the backend parses with
 * `date.fromisoformat`.
 */
export interface DateRange {
  startDate?: string | null;
  endDate?: string | null;
}

/**
 * One SKU's replenishment plan (B4). Two dated actions across the
 * supplier -> internal -> ML Full chain. Velocity is ML-channel-scoped.
 */
export interface ReplenishmentRow {
  product_id: number;
  product_name: string;
  product_sku: string | null;
  supplier_id: number | null;
  daily_velocity: number;
  internal_on_hand: number;
  full_on_hand: number;
  in_transit_to_full: number;
  full_available: number;
  days_cover_full: number;
  days_cover_pipeline: number;
  /** Suggested units to ship internal -> Full (capped at internal on-hand). */
  send_to_full_qty: number;
  /** ISO date, or null when no transfer is due. */
  send_to_full_by: string | null;
  supplier_lead_time_days: number | null;
  reorder_qty: number;
  /** ISO date, or null when no reorder is due. */
  reorder_by: string | null;
  /** 'critical' | 'soon' | 'watch' | 'ok'. */
  severity: string;
}

export interface ReplenishmentReport {
  rows: ReplenishmentRow[];
  velocity_window_days: number;
  full_transfer_lead_days: number;
  target_cover_days: number;
  total_send_now: number;
  total_reorder_now: number;
}

/**
 * One marketplace listing's margin-floor analysis (B6). Rates are the
 * effective fee (fraction of price) + shipping (per unit) used for the
 * floor; `rate_source` says whether they came from settled data.
 */
export interface RepricingRow {
  listing_id: number;
  product_id: number | null;
  product_name: string | null;
  product_sku: string | null;
  marketplace_id: number;
  marketplace_name: string;
  external_listing_id: string | null;
  cost_price: number;
  current_price: number;
  effective_fee_rate: number;
  shipping_per_unit: number;
  rate_source: string; // 'settled' | 'estimated'
  current_margin_percent: number | null;
  margin_floor_percent: number;
  suggested_price: number | null;
  suggested_margin_percent: number | null;
  status: string; // 'loss' | 'below_floor' | 'infeasible'
}

export interface RepricingReport {
  rows: RepricingRow[];
  margin_floor_percent: number;
  total_loss: number;
  total_below_floor: number;
}

export interface ApplyPriceResponse {
  listing_id: number;
  marketplace_price: number;
}

@Injectable({ providedIn: 'root' })
export class AnalyticsReportsService {
  private apiUrl = `${environment.apiUrl}/reports`;

  constructor(private http: HttpClient) {}

  exportVelocityCsv(windowDays = 30, limit = 2000, range?: DateRange): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/velocity/export`, this.withRange({ window_days: windowDays, limit }, range));
  }

  exportVelocityPdf(windowDays = 30, limit = 2000, range?: DateRange): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/velocity/export-pdf`, this.withRange({ window_days: windowDays, limit }, range));
  }

  exportMarginCsv(windowDays = 30, limit = 2000, range?: DateRange): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/margin/export`, this.withRange({ window_days: windowDays, limit }, range));
  }

  exportMarginPdf(windowDays = 30, limit = 2000, range?: DateRange): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/margin/export-pdf`, this.withRange({ window_days: windowDays, limit }, range));
  }

  exportStockoutCsv(
    windowDays = 30,
    imminentDays = 7,
    watchDays = 14,
    limit = 2000,
    range?: DateRange,
  ): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/stockout/export`, this.withRange({
      window_days: windowDays,
      imminent_days: imminentDays,
      watch_days: watchDays,
      limit,
    }, range));
  }

  exportStockoutPdf(
    windowDays = 30,
    imminentDays = 7,
    watchDays = 14,
    limit = 2000,
    range?: DateRange,
  ): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/stockout/export-pdf`, this.withRange({
      window_days: windowDays,
      imminent_days: imminentDays,
      watch_days: watchDays,
      limit,
    }, range));
  }

  exportRefundsSummaryCsv(windowDays = 30, range?: DateRange): Observable<Blob> {
    return this.blobGet(
      `${this.apiUrl}/refunds-summary/export`,
      this.withRange({ window_days: windowDays }, range),
    );
  }

  exportRefundsSummaryPdf(windowDays = 30, range?: DateRange): Observable<Blob> {
    return this.blobGet(
      `${this.apiUrl}/refunds-summary/export-pdf`,
      this.withRange({ window_days: windowDays }, range),
    );
  }

  exportReasonCodeSummaryCsv(windowDays = 30, range?: DateRange): Observable<Blob> {
    return this.blobGet(
      `${this.apiUrl}/reason-code-summary/export`,
      this.withRange({ window_days: windowDays }, range),
    );
  }

  exportReasonCodeSummaryPdf(windowDays = 30, range?: DateRange): Observable<Blob> {
    return this.blobGet(
      `${this.apiUrl}/reason-code-summary/export-pdf`,
      this.withRange({ window_days: windowDays }, range),
    );
  }

  private withRange(
    base: Record<string, number | string>,
    range?: DateRange,
  ): Record<string, number | string> {
    if (!range) return base;
    if (range.startDate) base['start_date'] = range.startDate;
    if (range.endDate) base['end_date'] = range.endDate;
    return base;
  }

  private blobGet(url: string, params: Record<string, number | string>): Observable<Blob> {
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
   * "¿Gané o perdí?" profit summary for a period. Contribution profit
   * minus operating expenses, resolved over one aligned window
   * server-side. Powers the profit-summary widget + the /reports/profit
   * page.
   */
  profitSummary(period: ProfitPeriod = 'this_month'): Observable<ProfitSummary> {
    const params = new HttpParams().set('period', period);
    return this.http.get<ProfitSummary>(`${this.apiUrl}/profit-summary`, { params });
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

  /**
   * Per-channel refund + cancellation rollup over the window.
   * Powers the dashboard's `RefundsWidget`. Numerator = orders that
   * transitioned out of the realized status set during the window
   * + Amazon partial-refund events posted in the window;
   * denominator = orders created in the window that are still
   * realized.
   */
  refundsSummary(windowDays = 30, range?: DateRange): Observable<RefundsSummaryResponse> {
    let params = new HttpParams().set('window_days', String(windowDays));
    if (range?.startDate) params = params.set('start_date', range.startDate);
    if (range?.endDate) params = params.set('end_date', range.endDate);
    return this.http.get<RefundsSummaryResponse>(
      `${this.apiUrl}/refunds-summary`, { params },
    );
  }

  /**
   * Per-channel physical-return rollup over the window. Powers the
   * dashboard returns widget. Mirrors `refundsSummary` (financial
   * side) but reads from `sales_order_returns` rows (physical
   * side). Cost-basis value, not retail.
   */
  returnsSummary(windowDays = 30, range?: DateRange): Observable<ReturnsSummaryResponse> {
    let params = new HttpParams().set('window_days', String(windowDays));
    if (range?.startDate) params = params.set('start_date', range.startDate);
    if (range?.endDate) params = params.set('end_date', range.endDate);
    return this.http.get<ReturnsSummaryResponse>(
      `${this.apiUrl}/returns-summary`, { params },
    );
  }

  /**
   * Per-event refund list — drill-down behind the dashboard widget.
   * Mixes `order_cancelled` rows (status transitions out of realized)
   * and `amazon_partial` rows (Amazon partial-refund events). Sorted
   * most-recent first.
   */
  refundsList(
    windowDays = 30,
    skip = 0,
    limit = 50,
    source?: string,
    range?: DateRange,
  ): Observable<RefundsListResponse> {
    let params = new HttpParams()
      .set('window_days', String(windowDays))
      .set('skip', String(skip))
      .set('limit', String(limit));
    if (source) params = params.set('source', source);
    if (range?.startDate) params = params.set('start_date', range.startDate);
    if (range?.endDate) params = params.set('end_date', range.endDate);
    return this.http.get<RefundsListResponse>(
      `${this.apiUrl}/refunds-list`, { params },
    );
  }

  /**
   * Per-event physical-returns list — drill-down behind the dashboard
   * returns widget. One row per `sales_order_returns` entry, sorted
   * most-recent first.
   */
  returnsList(
    windowDays = 30,
    skip = 0,
    limit = 50,
    source?: string,
    range?: DateRange,
  ): Observable<ReturnsListResponse> {
    let params = new HttpParams()
      .set('window_days', String(windowDays))
      .set('skip', String(skip))
      .set('limit', String(limit));
    if (source) params = params.set('source', source);
    if (range?.startDate) params = params.set('start_date', range.startDate);
    if (range?.endDate) params = params.set('end_date', range.endDate);
    return this.http.get<ReturnsListResponse>(
      `${this.apiUrl}/returns-list`, { params },
    );
  }

  questionsList(
    windowDays = 30,
    skip = 0,
    limit = 50,
    status?: string,
  ): Observable<QuestionsListResponse> {
    let params = new HttpParams()
      .set('window_days', String(windowDays))
      .set('skip', String(skip))
      .set('limit', String(limit));
    if (status) params = params.set('status', status);
    return this.http.get<QuestionsListResponse>(
      `${this.apiUrl}/questions`, { params },
    );
  }

  /**
   * Post a seller reply to a buyer question and return the updated row.
   * A 409 with `code: 'needs_reauthorization'` signals the caller should
   * surface an inline Reconnect affordance instead of a generic error.
   */
  answerQuestion(questionId: number, text: string): Observable<QuestionRow> {
    return this.http.post<QuestionRow>(
      `${this.apiUrl}/questions/${questionId}/answer`, { text },
    );
  }

  // -- B4: replenishment-to-Full planner ----------------------------

  /**
   * Per-SKU "reorder by / send to Full by" plan. Powers the
   * `/reports/replenishment` page. Server filters to ML-selling SKUs
   * that need an action.
   */
  replenishment(
    velocityWindowDays = 30,
    fullTransferLeadDays = 14,
    targetCoverDays = 30,
  ): Observable<ReplenishmentReport> {
    const params = new HttpParams()
      .set('velocity_window_days', String(velocityWindowDays))
      .set('full_transfer_lead_days', String(fullTransferLeadDays))
      .set('target_cover_days', String(targetCoverDays));
    return this.http.get<ReplenishmentReport>(
      `${this.apiUrl}/replenishment`, { params },
    );
  }

  exportReplenishmentCsv(
    velocityWindowDays = 30,
    fullTransferLeadDays = 14,
    targetCoverDays = 30,
  ): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/replenishment/export`, {
      velocity_window_days: velocityWindowDays,
      full_transfer_lead_days: fullTransferLeadDays,
      target_cover_days: targetCoverDays,
    });
  }

  exportReplenishmentPdf(
    velocityWindowDays = 30,
    fullTransferLeadDays = 14,
    targetCoverDays = 30,
  ): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/replenishment/export-pdf`, {
      velocity_window_days: velocityWindowDays,
      full_transfer_lead_days: fullTransferLeadDays,
      target_cover_days: targetCoverDays,
    });
  }

  // -- B6: margin-floor repricing assistant -------------------------

  /**
   * Listings priced below a target net-margin floor. Powers the
   * `/reports/repricing` page. `marginFloorPercent` is a whole-number
   * percent (e.g. 10 for 10%).
   */
  repricing(marginFloorPercent = 10): Observable<RepricingReport> {
    const params = new HttpParams().set('margin_floor_percent', String(marginFloorPercent));
    return this.http.get<RepricingReport>(`${this.apiUrl}/repricing`, { params });
  }

  /**
   * Push an approved price to the marketplace. A 409 with
   * `code: 'needs_reauthorization'` signals the caller should surface an
   * inline Reconnect affordance.
   */
  applyPrice(listingId: number, price: number): Observable<ApplyPriceResponse> {
    return this.http.post<ApplyPriceResponse>(
      `${this.apiUrl}/repricing/apply`, { listing_id: listingId, price },
    );
  }
}

export interface QuestionRow {
  id: number;
  external_question_id: string;
  source: string;
  item_id: string | null;
  /** Human product/listing title resolved from item_id; null when unresolved. */
  item_name?: string | null;
  buyer_id: string | null;
  question_text: string | null;
  answer_text: string | null;
  status: string | null;
  asked_at: string | null;
  answered_at: string | null;
  answered: boolean;
  /** Response time if answered, current open age otherwise (hours). */
  hours_open: number | null;
  /** 'answered' | 'pending' | 'breached'. */
  sla_status: string;
}

export interface QuestionsListResponse {
  rows: QuestionRow[];
  total: number;
  sla_hours: number;
  unanswered_count: number;
  breached_count: number;
  answered_count: number;
}
