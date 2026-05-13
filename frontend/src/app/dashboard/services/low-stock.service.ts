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
}
