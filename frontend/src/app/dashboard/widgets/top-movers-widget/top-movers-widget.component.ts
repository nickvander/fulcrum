import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { TranslocoModule } from '@ngneat/transloco';
import { finalize } from 'rxjs';

import {
  AnalyticsReportsService,
  TopMoverRow,
  TopMoversResponse,
} from '../../services/analytics-reports.service';

/**
 * "Top movers" leaderboard for the dashboard. Pulls the top 10
 * products by revenue over the last 30 days from
 * `GET /api/v1/reports/top-movers`. Each row carries per-product
 * net margin — the backend already pro-rates order-level fees +
 * shipping by revenue share, so the column reflects each product's
 * true contribution to the headline rollup.
 */
@Component({
  selector: 'app-top-movers-widget',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatTableModule,
    TranslocoModule,
  ],
  templateUrl: './top-movers-widget.component.html',
  styleUrls: ['./top-movers-widget.component.scss'],
})
export class TopMoversWidgetComponent implements OnInit {
  data: TopMoversResponse | null = null;
  loading = false;
  errored = false;
  windowDays = 30;
  limit = 10;

  readonly columns = ['name', 'units', 'revenue', 'profit', 'margin'];

  constructor(private analytics: AnalyticsReportsService) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading = true;
    this.errored = false;
    this.analytics.topMovers(this.windowDays, this.limit)
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: r => (this.data = r),
        error: () => (this.errored = true),
      });
  }

  formatCurrency(value: number): string {
    return value.toLocaleString('en-US', {
      style: 'currency', currency: 'MXN', maximumFractionDigits: 0,
    });
  }

  formatMargin(value: number | null | undefined): string {
    if (value === null || value === undefined) return '—';
    return `${value.toFixed(1)}%`;
  }

  /** Margin column color: red below 0%, orange below 10%, default
   *  otherwise. Quick visual triage for the operator scanning a
   *  page of products. */
  marginClass(row: TopMoverRow): string {
    const m = row.net_margin_percent;
    if (m === null || m === undefined) return '';
    if (m < 0) return 'margin-negative';
    if (m < 10) return 'margin-warn';
    return '';
  }
}
