import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule } from '@ngneat/transloco';
import { finalize } from 'rxjs';

import {
  AnalyticsReportsService,
  ReturnsListResponse,
  ReturnsListRow,
} from '../../services/analytics-reports.service';

/**
 * Returns drill-down page (`/reports/returns`).
 *
 * Per-event detail behind the dashboard's returns widget. Lists every
 * physical return recorded in the window — one row per
 * `sales_order_returns` entry — most-recent first, with a source
 * filter + paginator.
 *
 * Mirrors the refunds page so operators triaging a bad week can keep
 * the same UI mental model. Distinguished by:
 *   - "Value at cost" instead of "amount refunded": returns are
 *     accounted at COGS, refunds at revenue.
 *   - Product columns instead of order-status columns: the operator
 *     reading this page wants to spot which SKU is coming back.
 */
@Component({
  selector: 'app-returns-page',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTableModule,
    MatTooltipModule,
    TranslocoModule,
  ],
  templateUrl: './returns-page.component.html',
  styleUrls: ['./returns-page.component.scss'],
})
export class ReturnsPageComponent implements OnInit {
  windowDays: 30 | 60 | 90 | 180 = 30;
  /** Source filter: '' = all channels. */
  sourceFilter: '' | 'AMAZON' | 'MERCADOLIBRE' | 'FULCRUM' = '';

  pageIndex = 0;
  pageSize = 50;
  totalRows = 0;

  rows: ReturnsListRow[] = [];
  windowLabel = '';
  loading = false;
  errored = false;

  readonly displayedColumns = [
    'received_at',
    'source',
    'external_order_id',
    'product',
    'quantity',
    'reason',
    'value_at_cost',
    'actions',
  ];

  readonly windowOptions: Array<{ value: 30 | 60 | 90 | 180; labelKey: string }> = [
    { value: 30, labelKey: 'dashboard.returnsPage.window30' },
    { value: 60, labelKey: 'dashboard.returnsPage.window60' },
    { value: 90, labelKey: 'dashboard.returnsPage.window90' },
    { value: 180, labelKey: 'dashboard.returnsPage.window180' },
  ];

  readonly sourceOptions: Array<{ value: '' | 'AMAZON' | 'MERCADOLIBRE' | 'FULCRUM'; labelKey: string }> = [
    { value: '', labelKey: 'dashboard.returnsPage.sourceAll' },
    { value: 'MERCADOLIBRE', labelKey: 'dashboard.returnsPage.sourceMercadoLibre' },
    { value: 'AMAZON', labelKey: 'dashboard.returnsPage.sourceAmazon' },
    { value: 'FULCRUM', labelKey: 'dashboard.returnsPage.sourceFulcrum' },
  ];

  constructor(private analytics: AnalyticsReportsService) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.errored = false;
    const skip = this.pageIndex * this.pageSize;
    const sourceParam = this.sourceFilter === ''
      ? undefined
      : this.sourceFilter.toLowerCase();
    this.analytics
      .returnsList(this.windowDays, skip, this.pageSize, sourceParam)
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: (resp: ReturnsListResponse) => {
          this.rows = resp.items;
          this.totalRows = resp.total;
          this.windowLabel = resp.window_label;
        },
        error: () => {
          this.errored = true;
          this.rows = [];
          this.totalRows = 0;
        },
      });
  }

  onFilterChange(): void {
    this.pageIndex = 0;
    this.load();
  }

  onPage(event: PageEvent): void {
    this.pageIndex = event.pageIndex;
    this.pageSize = event.pageSize;
    this.load();
  }

  /** Channel label — brands stay English on both sides. */
  channelLabel(source: string | null): string {
    if (source === 'MERCADOLIBRE') return 'MercadoLibre';
    if (source === 'AMAZON') return 'Amazon';
    if (source === 'FULCRUM') return 'Fulcrum';
    return source || '—';
  }

  formatCurrency(value: number): string {
    return value.toLocaleString('en-US', {
      style: 'currency', currency: 'MXN', maximumFractionDigits: 2,
    });
  }
}
