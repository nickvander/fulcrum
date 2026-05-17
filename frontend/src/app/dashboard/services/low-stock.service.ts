import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export type LowStockSeverity = 'critical' | 'low' | 'watch';

export interface LowStockRow {
  product_id: number;
  product_name: string;
  product_sku?: string | null;
  supplier_id?: number | null;
  on_hand: number;
  threshold: number;
  reorder_point?: number | null;
  reorder_quantity?: number | null;
  suggested_reorder_qty: number;
  daily_velocity: number;
  days_of_inventory: number;
  severity: LowStockSeverity;
}

export interface LowStockReport {
  rows: LowStockRow[];
  total_critical: number;
  total_low: number;
  total_watch: number;
}

export interface CreatedReorderPO {
  purchase_order_id: number;
  supplier_id: number;
  supplier_name: string;
  product_count: number;
  total_amount: number;
}

export interface SkippedReorderProduct {
  product_id: number;
  product_name?: string | null;
  reason: 'no_supplier' | 'product_not_found' | string;
}

export interface ReorderResponse {
  created_purchase_orders: CreatedReorderPO[];
  skipped: SkippedReorderProduct[];
}

@Injectable({ providedIn: 'root' })
export class LowStockService {
  private apiUrl = `${environment.apiUrl}/reports/low-stock`;

  constructor(private http: HttpClient) {}

  getLowStock(limit = 50, velocityWindowDays = 30): Observable<LowStockReport> {
    const params = new HttpParams()
      .set('limit', limit.toString())
      .set('velocity_window_days', velocityWindowDays.toString());
    return this.http.get<LowStockReport>(this.apiUrl, { params });
  }

  /**
   * Download the low-stock report as a CSV file. Default limit is 500
   * (vs. 50 on the JSON endpoint) — the export use case is "give me
   * everything to triage in a spreadsheet".
   */
  exportLowStockCsv(limit = 500, velocityWindowDays = 30): Observable<Blob> {
    const params = new HttpParams()
      .set('limit', limit.toString())
      .set('velocity_window_days', velocityWindowDays.toString());
    return this.http.get(`${this.apiUrl}/export`, {
      params,
      responseType: 'blob',
    });
  }

  /**
   * Shopping-cart-style reorder. POSTs the selected product ids to the
   * backend, which groups them by primary supplier and creates one
   * DRAFT purchase order per supplier. Returns one summary per PO
   * created plus a `skipped` list for products that couldn't be
   * reordered (e.g. no supplier mapped).
   */
  reorderProducts(
    productIds: number[],
    quantityOverrides?: Record<number, number>,
  ): Observable<ReorderResponse> {
    return this.http.post<ReorderResponse>(`${this.apiUrl}/reorder`, {
      product_ids: productIds,
      quantity_overrides: quantityOverrides ?? null,
    });
  }
}
