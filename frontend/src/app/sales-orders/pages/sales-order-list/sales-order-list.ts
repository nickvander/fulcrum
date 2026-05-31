import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { TranslocoModule } from '@ngneat/transloco';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, finalize, takeUntil } from 'rxjs/operators';
import {
  OrderSource,
  SalesOrder,
  SalesOrdersService,
} from '../../services/sales-orders.service';
import { ReportDownloadService } from '../../../core/services/report-download.service';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';

@Component({
  selector: 'app-sales-order-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatTooltipModule,
    MatProgressBarModule,
    MatSelectModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    TranslocoModule,
    MoneyPipe,
    EmptyStateComponent,
  ],
  templateUrl: './sales-order-list.html',
  styleUrl: './sales-order-list.scss',
})
export class SalesOrderListComponent implements OnInit, OnDestroy {
  rows: SalesOrder[] = [];
  total = 0;
  loading = false;

  source: OrderSource | 'ALL' = 'ALL';
  days = 30;
  /** Bound to the search input; debounced through `search$` before it
   *  hits the server. Trimmed server-side too. */
  search = '';

  pageIndex = 0;
  pageSize = 25;
  readonly pageSizeOptions = [25, 50, 100];

  displayedColumns = ['created_at', 'source', 'external', 'status', 'total', 'margin'];

  private readonly search$ = new Subject<string>();
  private readonly destroy$ = new Subject<void>();

  constructor(
    private salesOrders: SalesOrdersService,
    private reportDownloader: ReportDownloadService,
  ) {}

  /** The trimmed search term, or undefined when blank (so we never send
   *  an empty `search` param). */
  private get searchTerm(): string | undefined {
    const t = this.search.trim();
    return t.length ? t : undefined;
  }

  /** Build the filter shape from the current page state so the export
   *  covers the same scope as the on-screen table (incl. the search). */
  private currentExportFilters() {
    return {
      ...(this.source !== 'ALL' ? { source: this.source } : {}),
      ...(this.searchTerm ? { search: this.searchTerm } : {}),
      days: this.days,
    };
  }

  exportCsv(): void {
    this.reportDownloader.download(
      this.salesOrders.exportListCsv(this.currentExportFilters()),
      'fulcrum-sales-orders',
      'csv',
    );
  }

  exportPdf(): void {
    this.reportDownloader.download(
      this.salesOrders.exportListPdf(this.currentExportFilters()),
      'fulcrum-sales-orders',
      'pdf',
    );
  }

  ngOnInit(): void {
    // Debounce typing so we only hit the server when the operator pauses;
    // any change resets to page 0.
    this.search$
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntil(this.destroy$))
      .subscribe(() => {
        this.pageIndex = 0;
        this.load();
      });
    this.load();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  load(): void {
    this.loading = true;
    const opts = {
      ...(this.source !== 'ALL' ? { source: this.source } : {}),
      ...(this.searchTerm ? { search: this.searchTerm } : {}),
      days: this.days,
      skip: this.pageIndex * this.pageSize,
      limit: this.pageSize,
    };
    this.salesOrders
      .list(opts)
      .pipe(
        finalize(() => (this.loading = false)),
        takeUntil(this.destroy$),
      )
      .subscribe({
        next: (resp) => {
          this.rows = resp.items;
          this.total = resp.total;
        },
        error: () => {
          this.rows = [];
          this.total = 0;
        },
      });
  }

  /** Filters (source/window) reset paging and refetch. */
  onFilterChange(): void {
    this.pageIndex = 0;
    this.load();
  }

  onSearchChange(): void {
    this.search$.next(this.search);
  }

  onPage(event: PageEvent): void {
    this.pageIndex = event.pageIndex;
    this.pageSize = event.pageSize;
    this.load();
  }

  /** True when the operator is searching but got no rows back — distinct
   *  from an empty window (no orders at all in the range). */
  get hasActiveSearch(): boolean {
    return !!this.searchTerm;
  }

  sourceChipClass(source: OrderSource | null | undefined): string {
    if (!source) return '';
    return `source-chip ${source.toLowerCase()}`;
  }

  statusChipClass(status: string | null | undefined): string {
    if (!status) return 'status-unknown';
    const lower = status.toLowerCase();
    if (['paid', 'confirmed', 'completed', 'shipped'].includes(lower)) return 'status-good';
    if (['pending', 'processing'].includes(lower)) return 'status-pending';
    if (['cancelled', 'canceled', 'failed', 'refunded'].includes(lower)) return 'status-bad';
    return 'status-unknown';
  }

  /** Net margin is "healthy" ≥ 15%, "thin" 0–15%, "loss" < 0. Null/unknown
   *  gets no band (em-dash in the template). Kept in lockstep with the
   *  order-detail page's `marginClass()` so the two views can't drift. */
  marginClass(pct: number | null | undefined): string {
    if (pct === null || pct === undefined) return '';
    if (pct < 0) return 'margin-loss';
    if (pct < 15) return 'margin-thin';
    return 'margin-healthy';
  }
}
