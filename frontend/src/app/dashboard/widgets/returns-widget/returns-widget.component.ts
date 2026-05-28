import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule } from '@ngneat/transloco';
import { finalize } from 'rxjs';

import {
  AnalyticsReportsService,
  ReturnsByChannelRow,
  ReturnsSummaryResponse,
} from '../../services/analytics-reports.service';

/**
 * "Returns (last 30d)" dashboard widget.
 *
 * Mirrors the refunds widget but for *physical* returns recorded by
 * the returns workflow on each sales order. The refunds widget
 * answers "how much money went back out?"; this widget answers
 * "how much stock came back?" — the two together cover the
 * financial and physical sides of the return relationship.
 *
 * Cost-basis (not retail) for `value_at_cost_mxn` because the
 * operator's exposure on the returns pile is the dollars they need
 * to discount, recover via resale, or write off.
 *
 * Channels with zero activity in the window are hidden so the
 * widget doesn't render empty rows on a fresh workspace.
 */
@Component({
  selector: 'app-returns-widget',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    TranslocoModule,
  ],
  templateUrl: './returns-widget.component.html',
  styleUrls: ['./returns-widget.component.scss'],
})
export class ReturnsWidgetComponent implements OnInit {
  summary: ReturnsSummaryResponse | null = null;
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
    this.analytics.returnsSummary(this.WINDOW_DAYS)
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: s => (this.summary = s),
        error: () => (this.errored = true),
      });
  }

  visibleChannels(): ReturnsByChannelRow[] {
    if (!this.summary) return [];
    return this.summary.by_channel.filter(r => r.returns_count > 0);
  }

  formatCurrency(value: number | null | undefined): string {
    if (value === null || value === undefined) return '—';
    return value.toLocaleString('en-US', {
      style: 'currency', currency: 'MXN', maximumFractionDigits: 0,
    });
  }

  channelLabel(source: string): string {
    if (source === 'MERCADOLIBRE') return 'MercadoLibre';
    if (source === 'AMAZON') return 'Amazon';
    if (source === 'FULCRUM') return 'Fulcrum';
    if (source === 'UNKNOWN') return 'Unknown';
    return source;
  }
}
