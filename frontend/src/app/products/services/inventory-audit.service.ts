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
  reason: string | null;
  created_by: string | null;
}

export interface InventoryAdjustmentList {
  rows: InventoryAdjustmentRow[];
  total: number;
}

export interface InventoryAuditFilters {
  productId?: number | null;
  after?: string | null;   // ISO datetime
  before?: string | null;  // ISO datetime
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
    if (opts.skip != null) params = params.set('skip', String(opts.skip));
    if (opts.limit != null) params = params.set('limit', String(opts.limit));
    return this.http.get<InventoryAdjustmentList>(this.apiUrl, { params });
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
    return params;
  }
}
