import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export type OrderSource = 'FULCRUM' | 'MERCADOLIBRE' | 'AMAZON';

export interface SalesOrder {
  id: number;
  status?: string | null;
  total_price?: number | null;
  /** Order's currency (ISO 4217). Defaults to MXN. */
  currency?: string | null;
  created_at?: string | null;
  source?: OrderSource | null;
  external_order_id?: string | null;
  /** Net margin % from the order's cost breakdown. `null`/absent means
   *  "no margin data" (no breakdown row, or zero-revenue order) — the UI
   *  renders an em-dash, never 0%. */
  net_margin_percent?: number | null;
}

/** Paginated envelope for `GET /sales-orders/`. `total` is the
 *  filtered+searched count BEFORE skip/limit, for the server-side
 *  paginator's `[length]`. */
export interface SalesOrderListResponse {
  items: SalesOrder[];
  total: number;
  skip: number;
  limit: number;
}

export interface SalesOrderItem {
  id: number;
  product_id?: number | null;
  quantity?: number | null;
  price_per_unit?: number | null;
  /** Captured cost basis per unit — drives per-line margin. */
  cost_per_unit?: number | null;
  product_name?: string | null;
  product_sku?: string | null;
}

export interface OrderCostBreakdown {
  currency: string;
  exchange_rate_to_mxn: number;
  revenue_amount: number;
  revenue_amount_mxn: number;
  cogs_amount: number;
  marketplace_fees_amount: number;
  shipping_cost_amount: number;
  ad_spend_amount: number;
  other_cost_amount: number;
  total_cost_amount: number;
  net_profit_amount: number;
  net_margin_percent?: number | null;
  /** 'estimated' (default fee rate) | 'settled' (real finance-API numbers). */
  fees_source: string;
  fees_synced_at?: string | null;
  reversed_at?: string | null;
}

export interface OrderStatusEvent {
  from_status?: string | null;
  to_status: string;
  changed_at: string;
  source_signal: string;
}

export interface OrderRefundEvent {
  refund_id: string;
  posted_at?: string | null;
  refund_amount: number;
  currency: string;
}

export interface SalesOrderDetail extends SalesOrder {
  items: SalesOrderItem[];
  cost_breakdown?: OrderCostBreakdown | null;
  status_timeline?: OrderStatusEvent[];
  refund_events?: OrderRefundEvent[];
}

export interface SalesOrderChannelBreakdown {
  source: OrderSource;
  count: number;
  revenue: number;
}

export interface SalesOrderSummary {
  window_days: number;
  total_orders: number;
  total_revenue: number;
  open_orders: number;
  by_channel: SalesOrderChannelBreakdown[];
}

@Injectable({ providedIn: 'root' })
export class SalesOrdersService {
  private apiUrl = `${environment.apiUrl}/sales-orders`;

  constructor(private http: HttpClient) {}

  list(opts: {
    source?: OrderSource;
    status?: string;
    days?: number;
    search?: string;
    sort_by?: string;
    sort_dir?: 'asc' | 'desc';
    skip?: number;
    limit?: number;
  } = {}): Observable<SalesOrderListResponse> {
    let params = new HttpParams();
    if (opts.source) params = params.set('source', opts.source);
    if (opts.status) params = params.set('status', opts.status);
    if (opts.days != null) params = params.set('days', String(opts.days));
    if (opts.search) params = params.set('search', opts.search);
    if (opts.sort_by) params = params.set('sort_by', opts.sort_by);
    if (opts.sort_dir) params = params.set('sort_dir', opts.sort_dir);
    if (opts.skip != null) params = params.set('skip', String(opts.skip));
    if (opts.limit != null) params = params.set('limit', String(opts.limit));
    return this.http.get<SalesOrderListResponse>(`${this.apiUrl}/`, { params });
  }

  summary(days = 30): Observable<SalesOrderSummary> {
    return this.http.get<SalesOrderSummary>(`${this.apiUrl}/summary`, {
      params: new HttpParams().set('days', String(days)),
    });
  }

  /** Download the full sales orders list as CSV. Accepts the same filters
   *  as the JSON list endpoint plus a higher limit for "give me the
   *  whole quarter" exports. */
  exportListCsv(opts: { source?: string; status?: string; days?: number; search?: string; limit?: number } = {}): Observable<Blob> {
    let params = new HttpParams();
    if (opts.source) params = params.set('source', opts.source);
    if (opts.status) params = params.set('status', opts.status);
    if (opts.days != null) params = params.set('days', String(opts.days));
    if (opts.search) params = params.set('search', opts.search);
    if (opts.limit != null) params = params.set('limit', String(opts.limit));
    return this.http.get(`${this.apiUrl}/export`, { params, responseType: 'blob' });
  }

  exportListPdf(opts: { source?: string; status?: string; days?: number; search?: string; limit?: number } = {}): Observable<Blob> {
    let params = new HttpParams();
    if (opts.source) params = params.set('source', opts.source);
    if (opts.status) params = params.set('status', opts.status);
    if (opts.days != null) params = params.set('days', String(opts.days));
    if (opts.search) params = params.set('search', opts.search);
    if (opts.limit != null) params = params.set('limit', String(opts.limit));
    return this.http.get(`${this.apiUrl}/export-pdf`, { params, responseType: 'blob' });
  }

  /** Download the sales-by-channel summary as CSV. Returns a Blob so the
   *  caller can decide how to surface the download (object URL, etc.). */
  exportSummaryCsv(days = 30): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/summary/export`, {
      params: new HttpParams().set('days', String(days)),
      responseType: 'blob',
    });
  }

  /** Download the sales-by-channel summary as PDF. */
  exportSummaryPdf(days = 30): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/summary/export-pdf`, {
      params: new HttpParams().set('days', String(days)),
      responseType: 'blob',
    });
  }

  get(orderId: number): Observable<SalesOrderDetail> {
    return this.http.get<SalesOrderDetail>(`${this.apiUrl}/${orderId}`);
  }

  // --- Returns ------------------------------------------------------------

  listReturns(orderId: number): Observable<SalesOrderReturn[]> {
    return this.http.get<SalesOrderReturn[]>(
      `${this.apiUrl}/${orderId}/returns`,
    );
  }

  recordReturn(orderId: number, payload: RecordReturnPayload): Observable<SalesOrderReturn[]> {
    return this.http.post<SalesOrderReturn[]>(
      `${this.apiUrl}/${orderId}/returns`,
      payload,
    );
  }
}

export interface SalesOrderReturn {
  id: number;
  order_id: number;
  order_item_id?: number | null;
  product_id?: number | null;
  product_name?: string | null;
  product_sku?: string | null;
  quantity: number;
  received_at: string;
  recorded_by_user_id?: number | null;
  recorded_by_email?: string | null;
  reason?: string | null;
  notes?: string | null;
}

export interface RecordReturnLine {
  /** Send `order_item_id` when the return is against a known line
   *  item; the backend falls back to the item's product_id. Use
   *  `product_id` only for legacy unmapped line items. */
  order_item_id?: number | null;
  product_id?: number | null;
  quantity: number;
}

export interface RecordReturnPayload {
  lines: RecordReturnLine[];
  reason?: string | null;
  notes?: string | null;
}
