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
  RefundsListResponse,
  RefundsListRow,
} from '../../services/analytics-reports.service';

/**
 * Refunds drill-down page (`/reports/refunds`).
 *
 * Per-event detail behind the dashboard's refunds widget. Lists every
 * refund event in the window — full-order cancellations from the
 * status-event audit + Amazon partial-refund events — most-recent
 * first, with a source filter + paginator.
 *
 * Each row links back to the parent sales order so the operator can
 * click through to investigate (return tracking, customer notes,
 * etc.). The link is best-effort: order_id is always populated, but
 * external_order_id may be missing on stub rows.
 */
@Component({
  selector: 'app-refunds-page',
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
  templateUrl: './refunds-page.component.html',
  styleUrls: ['./refunds-page.component.scss'],
})
export class RefundsPageComponent implements OnInit {
  /** Window in days for the rolling lookup; matches the widget's
   *  default so the drill-down shows the same set the operator clicked
   *  in from. */
  windowDays: 30 | 60 | 90 | 180 = 30;
  /** Source filter: '' = all channels. */
  sourceFilter: '' | 'AMAZON' | 'MERCADOLIBRE' | 'FULCRUM' = '';

  /** Material paginator state. */
  pageIndex = 0;
  pageSize = 50;
  totalRows = 0;

  rows: RefundsListRow[] = [];
  windowLabel = '';
  loading = false;
  errored = false;

  readonly displayedColumns = [
    'refunded_at',
    'source',
    'external_order_id',
    'refund_kind',
    'order_status',
    'refunded_amount_mxn',
    'actions',
  ];

  readonly windowOptions: Array<{ value: 30 | 60 | 90 | 180; labelKey: string }> = [
    { value: 30, labelKey: 'dashboard.refundsPage.window30' },
    { value: 60, labelKey: 'dashboard.refundsPage.window60' },
    { value: 90, labelKey: 'dashboard.refundsPage.window90' },
    { value: 180, labelKey: 'dashboard.refundsPage.window180' },
  ];

  readonly sourceOptions: Array<{ value: '' | 'AMAZON' | 'MERCADOLIBRE' | 'FULCRUM'; labelKey: string }> = [
    { value: '', labelKey: 'dashboard.refundsPage.sourceAll' },
    { value: 'MERCADOLIBRE', labelKey: 'dashboard.refundsPage.sourceMercadoLibre' },
    { value: 'AMAZON', labelKey: 'dashboard.refundsPage.sourceAmazon' },
    { value: 'FULCRUM', labelKey: 'dashboard.refundsPage.sourceFulcrum' },
  ];

  constructor(private analytics: AnalyticsReportsService) {}

  ngOnInit(): void {
    this.load();
  }

  /** Re-issue the list query with the current filter + pagination
   *  state. Called on init + after any filter change. */
  load(): void {
    this.loading = true;
    this.errored = false;
    const skip = this.pageIndex * this.pageSize;
    const sourceParam = this.sourceFilter === ''
      ? undefined
      : this.sourceFilter.toLowerCase();
    this.analytics
      .refundsList(this.windowDays, skip, this.pageSize, sourceParam)
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: (resp: RefundsListResponse) => {
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

  /** Filter / window changes reset to page 0 — staying on page 5 of a
   *  filtered set the operator just narrowed wouldn't make sense. */
  onFilterChange(): void {
    this.pageIndex = 0;
    this.load();
  }

  onPage(event: PageEvent): void {
    this.pageIndex = event.pageIndex;
    this.pageSize = event.pageSize;
    this.load();
  }

  /** Human-readable channel label. Doesn't go through i18n because
   *  marketplace names are English-as-brand on both ML and Amazon. */
  channelLabel(source: string): string {
    if (source === 'MERCADOLIBRE') return 'MercadoLibre';
    if (source === 'AMAZON') return 'Amazon';
    if (source === 'FULCRUM') return 'Fulcrum';
    return source;
  }

  /** Color the refund-kind chip differently so the operator can spot
   *  the partial-refund rows at a glance — those represent active
   *  shipments where money came back but inventory didn't. */
  refundKindClass(kind: string): string {
    return kind === 'amazon_partial' ? 'chip-partial' : 'chip-cancelled';
  }

  formatCurrency(value: number): string {
    return value.toLocaleString('en-US', {
      style: 'currency', currency: 'MXN', maximumFractionDigits: 2,
    });
  }
}
