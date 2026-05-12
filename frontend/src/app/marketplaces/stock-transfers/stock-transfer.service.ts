import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export type StockTransferStatus =
  | 'draft'
  | 'shipped'
  | 'partially_received'
  | 'received'
  | 'cancelled';

export const STOCK_LOCATION_INTERNAL = 'default';
export const STOCK_LOCATION_ML_FULL = 'ml-full';
export const STOCK_LOCATION_AMAZON_FBA = 'amazon-fba';

export interface StockTransferProductRef {
  id: number;
  name: string;
  sku?: string | null;
}

export interface StockTransferItem {
  id: number;
  transfer_id: number;
  product_id: number;
  variant_id?: number | null;
  qty_planned: number;
  qty_shipped: number;
  qty_received: number;
  product?: StockTransferProductRef | null;
}

export interface StockTransfer {
  id: number;
  source_location: string;
  dest_location: string;
  status: StockTransferStatus;
  notes?: string | null;
  external_inbound_id?: string | null;
  shipped_at?: string | null;
  received_at?: string | null;
  created_at: string;
  updated_at: string;
  items: StockTransferItem[];
}

export interface StockTransferItemInput {
  product_id: number;
  variant_id?: number | null;
  qty_planned: number;
}

export interface StockTransferCreateInput {
  source_location?: string;
  dest_location: string;
  notes?: string | null;
  items: StockTransferItemInput[];
}

export interface StockTransferUpdateInput {
  source_location?: string;
  dest_location?: string;
  notes?: string | null;
  items?: StockTransferItemInput[];
}

export interface StockTransferReceiveLine {
  transfer_item_id?: number;
  product_id: number;
  variant_id?: number | null;
  quantity: number;
}

export interface SyncListingsUpdated {
  product_id: number;
  external_listing_id: string;
  qty: number;
  ok: boolean;
  error?: string;
}

export interface SyncListingsMissing {
  product_id: number;
  qty_to_publish: number;
}

export interface SyncListingsResult {
  updated: SyncListingsUpdated[];
  missing_listings: SyncListingsMissing[];
}

@Injectable({ providedIn: 'root' })
export class StockTransferService {
  private apiUrl = `${environment.apiUrl}/stock-transfers`;

  constructor(private http: HttpClient) {}

  list(status?: StockTransferStatus | null): Observable<StockTransfer[]> {
    let params = new HttpParams();
    if (status) {
      params = params.set('status', status);
    }
    return this.http.get<StockTransfer[]>(`${this.apiUrl}/`, { params });
  }

  get(id: number): Observable<StockTransfer> {
    return this.http.get<StockTransfer>(`${this.apiUrl}/${id}`);
  }

  create(payload: StockTransferCreateInput): Observable<StockTransfer> {
    return this.http.post<StockTransfer>(`${this.apiUrl}/`, payload);
  }

  update(id: number, payload: StockTransferUpdateInput): Observable<StockTransfer> {
    return this.http.put<StockTransfer>(`${this.apiUrl}/${id}`, payload);
  }

  ship(id: number, pushToMarketplace = false): Observable<StockTransfer> {
    let params = new HttpParams();
    if (pushToMarketplace) {
      params = params.set('push_to_marketplace', 'true');
    }
    return this.http.post<StockTransfer>(`${this.apiUrl}/${id}/ship`, {}, { params });
  }

  syncListings(id: number): Observable<SyncListingsResult> {
    return this.http.post<SyncListingsResult>(`${this.apiUrl}/${id}/sync-listings`, {});
  }

  receive(id: number, lines: StockTransferReceiveLine[]): Observable<StockTransfer> {
    return this.http.post<StockTransfer>(`${this.apiUrl}/${id}/receive`, lines);
  }

  cancel(id: number): Observable<StockTransfer> {
    return this.http.post<StockTransfer>(`${this.apiUrl}/${id}/cancel`, {});
  }

  delete(id: number): Observable<{ deleted: number }> {
    return this.http.delete<{ deleted: number }>(`${this.apiUrl}/${id}`);
  }
}
