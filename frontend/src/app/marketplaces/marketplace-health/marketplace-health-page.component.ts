import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { finalize } from 'rxjs';

import {
  HealthListResponse,
  MarketplaceCredentialHealth,
  MarketplaceHealthService,
  PollOrdersResult,
  ReconcileInboundResult,
} from './marketplace-health.service';

@Component({
  selector: 'app-marketplace-health-page',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTableModule,
    MatTooltipModule,
    TranslocoModule,
  ],
  templateUrl: './marketplace-health-page.component.html',
  styleUrls: ['./marketplace-health-page.component.scss'],
})
export class MarketplaceHealthPageComponent implements OnInit {
  rows: MarketplaceCredentialHealth[] = [];
  loading = false;
  orderPollStaleMinutes = 30;
  inboundReconcileStaleMinutes = 90;
  webhookDisconnectHours = 24;

  /** Per-row busy keyed by credential_id, so the spinner shows only
   *  on the row whose button was clicked. */
  polling = new Set<number>();
  reconciling = new Set<number>();

  /** Last action's result, keyed by credential_id, surfaced as a
   *  result chip on the row + as a snackbar. */
  lastPollResult = new Map<number, PollOrdersResult>();
  lastReconcileResult = new Map<number, ReconcileInboundResult>();

  readonly columns = [
    'marketplace',
    'auth',
    'order_poll',
    'webhooks',
    'inbound',
    'actions',
  ];

  constructor(
    private health: MarketplaceHealthService,
    private snackBar: MatSnackBar,
    private transloco: TranslocoService,
  ) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading = true;
    this.health.list()
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: (resp: HealthListResponse) => {
          this.rows = resp.items;
          this.orderPollStaleMinutes = resp.order_poll_stale_minutes;
          this.inboundReconcileStaleMinutes = resp.inbound_reconcile_stale_minutes;
          this.webhookDisconnectHours = resp.webhook_disconnect_hours;
        },
        error: () => this.snack('marketplaceHealth.errors.loadFailed'),
      });
  }

  pollOrders(row: MarketplaceCredentialHealth): void {
    if (this.polling.has(row.credential_id)) return;
    this.polling.add(row.credential_id);
    this.health.pollOrders(row.credential_id)
      .pipe(finalize(() => this.polling.delete(row.credential_id)))
      .subscribe({
        next: result => {
          this.lastPollResult.set(row.credential_id, result);
          this.applyRefreshedHealth(result.health);
          this.surfacePollResult(result);
        },
        error: () => this.snack('marketplaceHealth.errors.pollFailed'),
      });
  }

  reconcileInbound(row: MarketplaceCredentialHealth): void {
    if (this.reconciling.has(row.credential_id)) return;
    this.reconciling.add(row.credential_id);
    this.health.reconcileInbound(row.credential_id)
      .pipe(finalize(() => this.reconciling.delete(row.credential_id)))
      .subscribe({
        next: result => {
          this.lastReconcileResult.set(row.credential_id, result);
          this.applyRefreshedHealth(result.health);
          this.surfaceReconcileResult(result);
        },
        error: () => this.snack('marketplaceHealth.errors.reconcileFailed'),
      });
  }

  /** The action endpoints embed a refreshed health row so the UI can
   *  patch the table without a follow-up list call. */
  private applyRefreshedHealth(
    refreshed: MarketplaceCredentialHealth | null | undefined,
  ): void {
    if (!refreshed) return;
    const idx = this.rows.findIndex(r => r.credential_id === refreshed.credential_id);
    if (idx >= 0) {
      this.rows = [
        ...this.rows.slice(0, idx),
        refreshed,
        ...this.rows.slice(idx + 1),
      ];
    }
  }

  private surfacePollResult(result: PollOrdersResult): void {
    if (result.error === 'needs_reauthorization') {
      this.snack('marketplaceHealth.messages.pollNeedsReauth');
      return;
    }
    if (result.error === 'unsupported_marketplace') {
      this.snack('marketplaceHealth.messages.pollUnsupported');
      return;
    }
    if (result.error) {
      this.snack('marketplaceHealth.errors.pollFailed');
      return;
    }
    const params = {
      new: result.orders_new,
      updated: result.orders_updated,
      items: result.items_created,
    };
    this.snack(
      result.orders_new > 0
        ? this.transloco.translate('marketplaceHealth.messages.pollFound', params)
        : this.transloco.translate('marketplaceHealth.messages.pollNoNew'),
    );
  }

  private surfaceReconcileResult(result: ReconcileInboundResult): void {
    if (result.error === 'needs_reauthorization') {
      this.snack('marketplaceHealth.messages.reconcileNeedsReauth');
      return;
    }
    if (result.error === 'unsupported_marketplace') {
      this.snack('marketplaceHealth.messages.reconcileUnsupported');
      return;
    }
    if (result.error) {
      this.snack('marketplaceHealth.errors.reconcileFailed');
      return;
    }
    if (result.transfers_processed === 0) {
      this.snack(this.transloco.translate('marketplaceHealth.messages.reconcileEmpty'));
      return;
    }
    this.snack(
      this.transloco.translate('marketplaceHealth.messages.reconcileDone', {
        processed: result.transfers_processed,
        updated: result.transfers_updated,
        units: result.total_received_added,
      }),
    );
  }

  // ---- Row-level helpers consumed by the template -----------------

  authClass(row: MarketplaceCredentialHealth): string {
    return row.needs_reauthorization ? 'badge-error' : 'badge-ok';
  }

  pollClass(row: MarketplaceCredentialHealth): string {
    return row.orders_poll_stale ? 'badge-warn' : 'badge-ok';
  }

  inboundClass(row: MarketplaceCredentialHealth): string {
    if (row.inbound_open_count === 0) return 'badge-ok';
    return row.inbound_stale_count > 0 ? 'badge-warn' : 'badge-info';
  }

  /** Webhook column color: red when the subscription looks dead,
   *  orange when the 24h count is zero (but the credential is still
   *  too fresh to flag), green otherwise. */
  webhookClass(row: MarketplaceCredentialHealth): string {
    if (row.webhook_likely_disconnected) return 'badge-error';
    if (row.webhooks_received_last_24h === 0) return 'badge-warn';
    return 'badge-ok';
  }

  /** Compact "Xm ago" / "Xh ago" without pulling in a date lib. */
  ago(iso: string | null | undefined): string {
    if (!iso) return this.transloco.translate('marketplaceHealth.never');
    const then = new Date(iso).getTime();
    if (isNaN(then)) return '—';
    const diffMs = Date.now() - then;
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return this.transloco.translate('marketplaceHealth.justNow');
    if (diffMin < 60) return `${diffMin}m`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h`;
    const diffDay = Math.floor(diffHr / 24);
    return `${diffDay}d`;
  }

  isBusy(row: MarketplaceCredentialHealth): boolean {
    return this.polling.has(row.credential_id)
      || this.reconciling.has(row.credential_id);
  }

  private snack(keyOrMessage: string): void {
    const message = keyOrMessage.includes(' ')
      ? keyOrMessage
      : this.transloco.translate(keyOrMessage);
    this.snackBar.open(
      message,
      this.transloco.translate('common.close'),
      { duration: 4000 },
    );
  }
}
