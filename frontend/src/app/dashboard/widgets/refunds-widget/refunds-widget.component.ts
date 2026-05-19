import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule } from '@ngneat/transloco';
import { finalize } from 'rxjs';

import {
  AnalyticsReportsService,
  RefundsByChannelRow,
  RefundsSummaryResponse,
} from '../../services/analytics-reports.service';

/**
 * "Refunds (last 30d)" dashboard widget.
 *
 * Aggregates marketplace-side refunds + cancellations from
 * `GET /reports/refunds-summary`. Surfaces total refund count +
 * refunded MXN + rate, with a per-channel breakdown so the
 * operator can tell whether a spike is ML-side or Amazon-side.
 *
 * Data sources behind the endpoint:
 *   - Full-order refunds/cancellations: status transitions out of
 *     the realized set, captured by the lifecycle hook.
 *   - Amazon partial refunds: `amazon_order_refunds` table,
 *     persisted by the settlement-fee worker.
 *
 * Channels with zero orders + zero refunds in the window are
 * hidden so a fresh workspace doesn't render three empty rows.
 */
@Component({
  selector: 'app-refunds-widget',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    TranslocoModule,
  ],
  templateUrl: './refunds-widget.component.html',
  styleUrls: ['./refunds-widget.component.scss'],
})
export class RefundsWidgetComponent implements OnInit {
  summary: RefundsSummaryResponse | null = null;
  loading = false;
  errored = false;
  readonly WINDOW_DAYS = 30;

  constructor(private analytics: AnalyticsReportsService) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading = true;
    this.errored = false;
    this.analytics.refundsSummary(this.WINDOW_DAYS)
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: s => (this.summary = s),
        error: () => (this.errored = true),
      });
  }

  /** Hide channels with zero history (no orders + no refunds). A
   *  fresh workspace shouldn't render three empty rows; an active
   *  workspace with one quiet channel shouldn't either. */
  visibleChannels(): RefundsByChannelRow[] {
    if (!this.summary) return [];
    return this.summary.by_channel.filter(
      r => r.refunds_count > 0 || r.realized_orders_count > 0,
    );
  }

  formatCurrency(value: number | null | undefined): string {
    if (value === null || value === undefined) return '—';
    return value.toLocaleString('en-US', {
      style: 'currency', currency: 'MXN', maximumFractionDigits: 0,
    });
  }

  formatRate(value: number | null | undefined): string {
    if (value === null || value === undefined) return '—';
    return `${value.toFixed(1)}%`;
  }

  /** Color the rate red above 5% — a rough industry-bad threshold;
   *  amber above 2%; green otherwise. The dashboard widget is for
   *  glanceable awareness, not policy enforcement. */
  rateClass(value: number | null | undefined): string {
    if (value === null || value === undefined) return '';
    if (value >= 5) return 'rate-high';
    if (value >= 2) return 'rate-warn';
    return 'rate-ok';
  }

  /** Channel labels — capitalize for display without committing to
   *  a full i18n key per channel name (the marketplace name is
   *  English-as-brand on both ML and Amazon). */
  channelLabel(source: string): string {
    if (source === 'MERCADOLIBRE') return 'MercadoLibre';
    if (source === 'AMAZON') return 'Amazon';
    if (source === 'FULCRUM') return 'Fulcrum';
    return source;
  }
}
