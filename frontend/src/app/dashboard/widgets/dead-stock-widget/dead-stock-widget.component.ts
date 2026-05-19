import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule } from '@ngneat/transloco';
import { finalize } from 'rxjs';

import {
  AnalyticsReportsService,
  DeadStockResponse,
  DeadStockRow,
} from '../../services/analytics-reports.service';

/**
 * "Dead stock" leaderboard for the dashboard. Surfaces products
 * with on-hand inventory but near-zero recent sales velocity —
 * the SKUs an operator should discount, bundle, or stop reordering
 * before capital sits idle.
 *
 * Reads `/api/v1/reports/dead-stock` with the backend's default
 * 0.1 units/day threshold over a 30-day window. The widget header
 * surfaces the actual thresholds from the response envelope so the
 * UI and backend stay in sync without duplicated constants.
 */
@Component({
  selector: 'app-dead-stock-widget',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTableModule,
    MatTooltipModule,
    TranslocoModule,
  ],
  templateUrl: './dead-stock-widget.component.html',
  styleUrls: ['./dead-stock-widget.component.scss'],
})
export class DeadStockWidgetComponent implements OnInit {
  data: DeadStockResponse | null = null;
  loading = false;
  errored = false;
  windowDays = 30;
  thresholdDailyVelocity = 0.1;
  limit = 20;

  readonly columns = ['product', 'on_hand', 'last_sale', 'value'];

  constructor(private analytics: AnalyticsReportsService) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading = true;
    this.errored = false;
    this.analytics.deadStock(
      this.windowDays, this.thresholdDailyVelocity, this.limit,
    )
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: r => (this.data = r),
        error: () => (this.errored = true),
      });
  }

  formatCurrency(value: number | null | undefined): string {
    if (value === null || value === undefined) return '—';
    return value.toLocaleString('en-US', {
      style: 'currency', currency: 'MXN', maximumFractionDigits: 0,
    });
  }

  /** Severity class for the "last sale" cell. Never-sold +
   *  90-day-dead get the strongest visual signal — that's where
   *  capital is most likely actually wasted vs. just a slow week. */
  ageClass(row: DeadStockRow): string {
    if (row.days_since_last_sale === null) return 'age-never';
    if (row.days_since_last_sale >= 90) return 'age-critical';
    if (row.days_since_last_sale >= 30) return 'age-warn';
    return '';
  }

  /** Total dollars-at-risk across the displayed rows. Renders in
   *  the widget header so the operator sees the aggregate impact
   *  even before scanning the table. */
  totalAtRisk(): number {
    if (!this.data) return 0;
    return this.data.rows.reduce(
      (sum, r) => sum + (r.stock_value_at_cost ?? 0),
      0,
    );
  }
}
