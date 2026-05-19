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

  /**
   * Most recent `WebhookEvent.received_at` for this credential's
   * marketplace (any topic). null when no events have arrived yet.
   * Webhooks are app-scoped, not user-scoped, so credentials for the
   * same marketplace share this value.
   */
  webhook_last_received_at?: string | null;
  webhooks_received_last_24h: number;
  /**
   * True when the credential is older than the disconnect threshold
   * AND no webhook events have arrived for its marketplace in the
   * same period. Catches both "subscription never configured" and
   * "subscription died" without false-positives on a freshly-
   * connected credential.
   */
  webhook_likely_disconnected: boolean;

  /**
   * Timestamp of the last successful settlement-fee sync run for this
   * credential. NULL until the first run completes. Powers the
   * marketplace-health page's "Settlement (last synced)" column so the
   * operator can tell whether the real settled-fee numbers powering
   * the dashboard's net-margin widgets are fresh.
   */
  last_settlement_synced_at?: string | null;
}

export interface HealthListResponse {
  items: MarketplaceCredentialHealth[];
  order_poll_stale_minutes: number;
  inbound_reconcile_stale_minutes: number;
  webhook_disconnect_hours: number;
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

export interface SettlementSyncResult {
  credential_id: number;
  marketplace_name: string;
  /** Breakdown rows flipped from `estimated` → `settled` this run. */
  orders_settled: number;
  /** Orders whose marketplace returned no fee data yet — retried next tick. */
  orders_pending: number;
  errors: number;
  /** Total orders considered (capped at MAX_BATCH per credential). */
  scanned: number;
  error?: string | null;
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

  syncSettlementFees(credentialId: number): Observable<SettlementSyncResult> {
    return this.http.post<SettlementSyncResult>(
      `${this.apiUrl}/${credentialId}/sync-settlement-fees`, {},
    );
  }
}
