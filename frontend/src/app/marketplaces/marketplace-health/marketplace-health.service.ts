import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface MarketplaceCredentialHealth {
  credential_id: number;
  marketplace_id: number;
  marketplace_name: string;
  user_id: number;

  needs_reauthorization: boolean;
  last_refresh_error?: string | null;
  expires_at?: string | null;

  last_orders_polled_at?: string | null;
  orders_poll_stale: boolean;

  inbound_open_count: number;
  inbound_stale_count: number;
}

export interface HealthListResponse {
  items: MarketplaceCredentialHealth[];
  order_poll_stale_minutes: number;
  inbound_reconcile_stale_minutes: number;
}

export interface PollOrdersResult {
  credential_id: number;
  marketplace_name: string;
  orders_new: number;
  orders_updated: number;
  orders_skipped: number;
  items_created: number;
  error?: string | null;
  health?: MarketplaceCredentialHealth | null;
}

export interface PerTransferReconcile {
  transfer_id: number;
  items_updated?: number;
  total_received_added?: number;
  status_before?: string | null;
  status_after?: string | null;
  skipped_reason?: string | null;
  unmapped_listings?: string[];
  error?: string;
}

export interface ReconcileInboundResult {
  credential_id: number;
  marketplace_name: string;
  transfers_processed: number;
  transfers_updated: number;
  total_received_added: number;
  error?: string | null;
  per_transfer: PerTransferReconcile[];
  health?: MarketplaceCredentialHealth | null;
}

/**
 * Thin HTTP wrapper around the operator-facing
 * `/api/v1/marketplaces/health` surface. Pairs with
 * `MarketplaceHealthPageComponent` which renders the rollup +
 * "Poll now" / "Reconcile now" buttons per credential.
 *
 * No state — the page caches the list in its own component.
 */
@Injectable({ providedIn: 'root' })
export class MarketplaceHealthService {
  private apiUrl = `${environment.apiUrl}/marketplaces/health`;

  constructor(private http: HttpClient) {}

  list(): Observable<HealthListResponse> {
    return this.http.get<HealthListResponse>(`${this.apiUrl}/`);
  }

  pollOrders(credentialId: number): Observable<PollOrdersResult> {
    return this.http.post<PollOrdersResult>(
      `${this.apiUrl}/${credentialId}/poll-orders`, {},
    );
  }

  reconcileInbound(credentialId: number): Observable<ReconcileInboundResult> {
    return this.http.post<ReconcileInboundResult>(
      `${this.apiUrl}/${credentialId}/reconcile-inbound`, {},
    );
  }
}
