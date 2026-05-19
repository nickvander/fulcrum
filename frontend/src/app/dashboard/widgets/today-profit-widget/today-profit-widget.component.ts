import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule } from '@ngneat/transloco';
import { finalize } from 'rxjs';

import { AnalyticsReportsService, CostRollup } from '../../services/analytics-reports.service';

/**
 * "Today's profit" ticker for the dashboard.
 *
 * Calls `cost-rollup?window_days=1` so the headline number reflects
 * realized sales over the last 24h. The breakdown card below shows
 * revenue / total cost / margin % so the operator can tell at a
 * glance whether margin is on track even when revenue is high.
 */
@Component({
  selector: 'app-today-profit-widget',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    TranslocoModule,
  ],
  templateUrl: './today-profit-widget.component.html',
  styleUrls: ['./today-profit-widget.component.scss'],
})
export class TodayProfitWidgetComponent implements OnInit {
  rollup: CostRollup | null = null;
  loading = false;
  errored = false;

  constructor(private analytics: AnalyticsReportsService) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading = true;
    this.errored = false;
    this.analytics.costRollup(1)
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: r => (this.rollup = r),
        error: () => (this.errored = true),
      });
  }

  formatCurrency(value: number | null | undefined): string {
    if (value === null || value === undefined) return '—';
    return value.toLocaleString('en-US', {
      style: 'currency', currency: 'MXN', maximumFractionDigits: 0,
    });
  }

  formatMargin(value: number | null | undefined): string {
    if (value === null || value === undefined) return '—';
    return `${value.toFixed(1)}%`;
  }

  /** Color the profit number red when it goes negative — quick
   *  visual flag for a bad day. */
  profitClass(): string {
    if (!this.rollup) return '';
    const profit = this.rollup.net_profit_amount;
    if (profit < 0) return 'profit-negative';
    if (profit === 0) return 'profit-zero';
    return 'profit-positive';
  }
}
