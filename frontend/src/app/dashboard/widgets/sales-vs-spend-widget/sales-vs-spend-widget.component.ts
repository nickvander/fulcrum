import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslocoModule } from '@ngneat/transloco';
import { finalize } from 'rxjs';

import {
  AnalyticsReportsService,
  CostRollupDailyResponse,
  CostRollupDailyRow,
} from '../../services/analytics-reports.service';

/**
 * "Sales vs spend over time" line chart for the dashboard.
 *
 * Hand-rolled SVG so we don't drag in a chart library for two
 * lines. Two stacked y-aware polylines (revenue + total cost)
 * over a configurable window. Gap-free x-axis: zero days are
 * emitted as zero-valued rows by the backend.
 */
@Component({
  selector: 'app-sales-vs-spend-widget',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatProgressSpinnerModule,
    TranslocoModule,
  ],
  templateUrl: './sales-vs-spend-widget.component.html',
  styleUrls: ['./sales-vs-spend-widget.component.scss'],
})
export class SalesVsSpendWidgetComponent implements OnInit {
  data: CostRollupDailyResponse | null = null;
  loading = false;
  errored = false;
  windowDays = 30;

  // Logical SVG canvas — viewBox-based so CSS scales it. Numbers are
  // exposed for tests; production CSS sets responsive width.
  readonly CANVAS_WIDTH = 480;
  readonly CANVAS_HEIGHT = 160;
  readonly PADDING_X = 10;
  readonly PADDING_Y = 12;

  constructor(private analytics: AnalyticsReportsService) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading = true;
    this.errored = false;
    this.analytics.costRollupDaily(this.windowDays)
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: r => (this.data = r),
        error: () => (this.errored = true),
      });
  }

  /** Max y-value across both series, used to scale the lines. Floor
   *  at 1 so a flat-zero series doesn't divide by zero. */
  get maxValue(): number {
    if (!this.data || this.data.series.length === 0) return 1;
    let max = 0;
    for (const row of this.data.series) {
      if (row.revenue_amount_mxn > max) max = row.revenue_amount_mxn;
      if (row.total_cost_amount > max) max = row.total_cost_amount;
    }
    return Math.max(1, max);
  }

  /** Map a series row's index → x pixel. Equally spaced across the
   *  drawable inner width. */
  xFor(index: number): number {
    if (!this.data || this.data.series.length <= 1) return this.PADDING_X;
    const inner = this.CANVAS_WIDTH - 2 * this.PADDING_X;
    return this.PADDING_X + (index / (this.data.series.length - 1)) * inner;
  }

  /** Map a value → y pixel. y=0 at the bottom of the drawable area. */
  yFor(value: number): number {
    const inner = this.CANVAS_HEIGHT - 2 * this.PADDING_Y;
    const ratio = Math.min(1, Math.max(0, value / this.maxValue));
    return this.PADDING_Y + (1 - ratio) * inner;
  }

  /** Build the SVG polyline `points` attribute for one series. */
  polyline(series: 'revenue' | 'cost'): string {
    if (!this.data) return '';
    return this.data.series
      .map((row, i) => {
        const v = series === 'revenue'
          ? row.revenue_amount_mxn
          : row.total_cost_amount;
        return `${this.xFor(i).toFixed(2)},${this.yFor(v).toFixed(2)}`;
      })
      .join(' ');
  }

  /** Aggregate totals shown below the chart so the operator sees
   *  the numbers the lines depict. */
  totals(): { revenue: number; cost: number; profit: number; orders: number } {
    if (!this.data) return { revenue: 0, cost: 0, profit: 0, orders: 0 };
    let revenue = 0, cost = 0, profit = 0, orders = 0;
    for (const row of this.data.series) {
      revenue += row.revenue_amount_mxn;
      cost += row.total_cost_amount;
      profit += row.net_profit_amount;
      orders += row.orders;
    }
    return { revenue, cost, profit, orders };
  }

  formatCurrency(value: number): string {
    return value.toLocaleString('en-US', {
      style: 'currency', currency: 'MXN', maximumFractionDigits: 0,
    });
  }

  shortDate(iso: string): string {
    // The backend emits date-only ISO strings (YYYY-MM-DD). Parsing
    // those with `new Date(iso)` interprets them as UTC midnight,
    // which drifts a day off when displayed in any timezone west of
    // UTC. Parse the components directly to keep the calendar day
    // stable regardless of the user's tz.
    const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
    if (!match) return '';
    const month = parseInt(match[2], 10);
    const day = parseInt(match[3], 10);
    if (isNaN(month) || isNaN(day)) return '';
    return `${month}/${day}`;
  }

  /** First / last x-axis labels so the operator can read the range
   *  without rendering every day's label. */
  axisLabels(): { left: string; right: string } | null {
    if (!this.data || this.data.series.length === 0) return null;
    return {
      left: this.shortDate(this.data.series[0].date),
      right: this.shortDate(this.data.series[this.data.series.length - 1].date),
    };
  }

  hasData(): boolean {
    if (!this.data) return false;
    return this.data.series.some(
      row => row.revenue_amount_mxn > 0 || row.total_cost_amount > 0,
    );
  }
}
