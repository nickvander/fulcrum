import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';


export type InventoryCountSessionStatus = 'in_progress' | 'committed' | 'cancelled';


export interface InventoryCountItem {
  id: number;
  session_id: number;
  product_id: number;
  variant_id: number | null;
  product_sku: string | null;
  product_name: string | null;
  expected_quantity: number;
  counted_quantity: number | null;
  added_at: string;
  updated_at: string | null;
}


export interface InventoryCountSessionHeader {
  id: number;
  status: InventoryCountSessionStatus;
  location: string;
  notes: string | null;
  started_at: string;
  ended_at: string | null;
  started_by_user_id: number | null;
  started_by_email: string | null;
  item_count: number;
}


export interface InventoryCountSessionDetail extends InventoryCountSessionHeader {
  items: InventoryCountItem[];
}


export interface InventoryCountCommitResult {
  adjustments_created: number;
  items_skipped: number;
  session: InventoryCountSessionDetail;
}


/**
 * Thin HTTP wrapper around `/api/v1/inventory-counts`. The page
 * components drive the state machine (start → add → count → commit
 * / cancel) by chaining these methods.
 */
@Injectable({ providedIn: 'root' })
export class InventoryCountService {
  private readonly apiUrl = `${environment.apiUrl}/inventory-counts`;

  constructor(private http: HttpClient) {}

  list(opts: { status?: InventoryCountSessionStatus | null; limit?: number } = {}): Observable<InventoryCountSessionHeader[]> {
    const params: Record<string, string> = {};
    if (opts.status) params['status'] = opts.status;
    if (opts.limit != null) params['limit'] = String(opts.limit);
    return this.http.get<InventoryCountSessionHeader[]>(`${this.apiUrl}/`, { params });
  }

  start(payload: { location?: string; notes?: string } = {}): Observable<InventoryCountSessionDetail> {
    return this.http.post<InventoryCountSessionDetail>(`${this.apiUrl}/`, payload);
  }

  get(sessionId: number): Observable<InventoryCountSessionDetail> {
    return this.http.get<InventoryCountSessionDetail>(`${this.apiUrl}/${sessionId}`);
  }

  addItem(sessionId: number, sku: string): Observable<InventoryCountItem> {
    return this.http.post<InventoryCountItem>(
      `${this.apiUrl}/${sessionId}/items`,
      { sku },
    );
  }

  updateCount(
    sessionId: number, itemId: number, countedQuantity: number | null,
  ): Observable<InventoryCountItem> {
    return this.http.patch<InventoryCountItem>(
      `${this.apiUrl}/${sessionId}/items/${itemId}`,
      { counted_quantity: countedQuantity },
    );
  }

  removeItem(sessionId: number, itemId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${sessionId}/items/${itemId}`);
  }

  commit(sessionId: number): Observable<InventoryCountCommitResult> {
    return this.http.post<InventoryCountCommitResult>(
      `${this.apiUrl}/${sessionId}/commit`, {},
    );
  }

  cancel(sessionId: number): Observable<InventoryCountSessionDetail> {
    return this.http.post<InventoryCountSessionDetail>(
      `${this.apiUrl}/${sessionId}/cancel`, {},
    );
  }
}
