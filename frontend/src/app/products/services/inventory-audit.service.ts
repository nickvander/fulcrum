import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';

export interface InventoryAdjustmentRow {
  id: number;
  timestamp: string | null;
  product_id: number | null;
  product_sku: string | null;
  product_name: string | null;
  adjustment: number;
  /** Typed taxonomy (`shrinkage` / `recount` / `damage` / `return` /
   *  `theft` / `correction` / `sale` / `cancellation` / `transfer` /
   *  `purchase` / `manual` / `other`). NULL on legacy pre-migration
   *  rows — the audit-page dropdown renders those as
   *  "Uncategorized". */
  reason_code: string | null;
  reason: string | null;
  created_by: string | null;
  /** Set when THIS row is a correction undoing an earlier adjustment. */
  reverses_adjustment_id?: number | null;
  /** Set when this row HAS BEEN reversed by a later correction. */
  reversed_by_id?: number | null;
  /** Whether the operator can reverse this row (operator-reversible
   *  reason code, not already reversed, not itself a reversal). */
  reversible?: boolean;
}

export interface InventoryAdjustmentList {
  rows: InventoryAdjustmentRow[];
  total: number;
}

export interface InventoryAuditFilters {
  productId?: number | null;
  after?: string | null;   // ISO datetime
  before?: string | null;  // ISO datetime
  /** Send a known enum value to filter to that reason, or the magic
   *  string `'none'` to filter to legacy uncategorized (NULL) rows. */
  reasonCode?: string | null;
}

@Injectable({ providedIn: 'root' })
export class InventoryAuditService {
  private readonly apiUrl = `${environment.apiUrl}/reports/inventory-adjustments`;

  constructor(private http: HttpClient) {}

  list(opts: InventoryAuditFilters & { skip?: number; limit?: number } = {}): Observable<InventoryAdjustmentList> {
    let params = new HttpParams();
    if (opts.productId != null) params = params.set('product_id', String(opts.productId));
    if (opts.after) params = params.set('after', opts.after);
    if (opts.before) params = params.set('before', opts.before);
    if (opts.reasonCode) params = params.set('reason_code', opts.reasonCode);
    if (opts.skip != null) params = params.set('skip', String(opts.skip));
    if (opts.limit != null) params = params.set('limit', String(opts.limit));
    return this.http.get<InventoryAdjustmentList>(this.apiUrl, { params });
  }

  /** Fetch the canonical reason-code list for the dropdown. Cached
   *  by the browser between page visits via the standard HTTP cache;
   *  the values rarely change. */
  listReasonCodes(): Observable<string[]> {
    return this.http.get<string[]>(`${this.apiUrl}/reason-codes`);
  }

  /** Reverse an operator adjustment — books an equal-and-opposite
   *  `correction` row linked to the original. Returns the new row. */
  reverse(adjustmentId: number, note?: string): Observable<InventoryAdjustmentRow> {
    return this.http.post<InventoryAdjustmentRow>(
      `${this.apiUrl}/${adjustmentId}/reverse`,
      { note: note ?? null },
    );
  }

  exportCsv(filters: InventoryAuditFilters = {}): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/export`, {
      params: this.buildExportParams(filters),
      responseType: 'blob',
    });
  }

  exportPdf(filters: InventoryAuditFilters = {}): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/export-pdf`, {
      params: this.buildExportParams(filters),
      responseType: 'blob',
    });
  }

  private buildExportParams(filters: InventoryAuditFilters): HttpParams {
    let params = new HttpParams();
    if (filters.productId != null) params = params.set('product_id', String(filters.productId));
    if (filters.after) params = params.set('after', filters.after);
    if (filters.before) params = params.set('before', filters.before);
    if (filters.reasonCode) params = params.set('reason_code', filters.reasonCode);
    return params;
  }
}
