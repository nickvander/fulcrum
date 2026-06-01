import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
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
import { MatSortModule, Sort, SortDirection } from '@angular/material/sort';
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
    MatSortModule,
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
  /** Selected order status, or 'ALL' for no status filter. */
  status: string | 'ALL' = 'ALL';
  days = 30;
  /** Bound to the search input; debounced through `search$` before it
   *  hits the server. Trimmed server-side too. */
  search = '';

  pageIndex = 0;
  pageSize = 25;
  readonly pageSizeOptions = [25, 50, 100];

  /** Server-side sort state. Defaults mirror the backend's default of
   *  `created_at desc`. The active value is a UI column id; it's mapped to
   *  the backend `sort_by` token via `COLUMN_TO_SORT_BY`. */
  sortActive = 'created_at';
  sortDirection: SortDirection = 'desc';

  displayedColumns = ['created_at', 'source', 'external', 'status', 'total', 'margin'];

  /** Order statuses the operator can filter by. Mirrors `statusChipClass()`
   *  and the statuses the ingestion/lifecycle services emit. */
  readonly statusOptions = [
    'PAID',
    'CONFIRMED',
    'COMPLETED',
    'SHIPPED',
    'PENDING',
    'PROCESSING',
    'CANCELLED',
    'REFUNDED',
  ];

  /** Maps a UI column id to the backend `sort_by` token. Most are 1:1; a
   *  few table column ids differ from the API column names. */
  private static readonly COLUMN_TO_SORT_BY: Record<string, string> = {
    created_at: 'created_at',
    status: 'status',
    source: 'source',
    external: 'external_order_id',
    total: 'total_price',
    margin: 'net_margin_percent',
  };

  private readonly search$ = new Subject<string>();
  private readonly destroy$ = new Subject<void>();

  constructor(
    private salesOrders: SalesOrdersService,
    private reportDownloader: ReportDownloadService,
    private router: Router,
    private route: ActivatedRoute,
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
      ...(this.status !== 'ALL' ? { status: this.status } : {}),
      ...(this.searchTerm ? { search: this.searchTerm } : {}),
      days: this.days,
    };
  }

  /** The backend `sort_by` token for the currently-active UI column. */
  private get sortBy(): string {
    return SalesOrderListComponent.COLUMN_TO_SORT_BY[this.sortActive] ?? 'created_at';
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
    // Restore the full view (filters/search/sort/page) from the URL before
    // the first fetch, so a refresh or back-navigation lands on the same
    // table the operator left.
    this.restoreFromQueryParams();

    // Debounce typing so we only hit the server when the operator pauses;
    // any change resets to page 0 and is merged into the URL.
    this.search$
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntil(this.destroy$))
      .subscribe(() => {
        this.pageIndex = 0;
        this.syncQueryParams();
        this.load();
      });
    this.load();
  }

  /** Read the saved view from the URL query params (snapshot — we only
   *  restore once, on init). Missing/invalid params keep their defaults. */
  private restoreFromQueryParams(): void {
    const p = this.route.snapshot.queryParams;
    if (p['source']) this.source = p['source'] as OrderSource | 'ALL';
    if (p['status']) this.status = p['status'];
    if (p['days'] != null && !Number.isNaN(+p['days'])) this.days = +p['days'];
    if (p['search']) this.search = p['search'];
    if (p['sort_by']) {
      // Map the persisted backend token back to the UI column id.
      const uiCol = Object.keys(SalesOrderListComponent.COLUMN_TO_SORT_BY).find(
        (k) => SalesOrderListComponent.COLUMN_TO_SORT_BY[k] === p['sort_by'],
      );
      if (uiCol) this.sortActive = uiCol;
    }
    if (p['sort_dir'] === 'asc' || p['sort_dir'] === 'desc') {
      this.sortDirection = p['sort_dir'];
    }
    if (p['page'] != null && !Number.isNaN(+p['page'])) this.pageIndex = +p['page'];
    if (p['size'] != null && this.pageSizeOptions.includes(+p['size'])) {
      this.pageSize = +p['size'];
    }
  }

  /** Write the current view to the URL via a merge navigation. Defaults are
   *  omitted (set to null) so the URL stays clean when nothing's customized. */
  private syncQueryParams(): void {
    const queryParams = {
      source: this.source !== 'ALL' ? this.source : null,
      status: this.status !== 'ALL' ? this.status : null,
      days: this.days !== 30 ? this.days : null,
      search: this.searchTerm ?? null,
      sort_by: this.sortBy !== 'created_at' ? this.sortBy : null,
      sort_dir:
        this.sortDirection && this.sortDirection !== 'desc' ? this.sortDirection : null,
      page: this.pageIndex !== 0 ? this.pageIndex : null,
      size: this.pageSize !== 25 ? this.pageSize : null,
    };
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams,
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  load(): void {
    this.loading = true;
    const opts = {
      ...(this.source !== 'ALL' ? { source: this.source } : {}),
      ...(this.status !== 'ALL' ? { status: this.status } : {}),
      ...(this.searchTerm ? { search: this.searchTerm } : {}),
      ...(this.sortBy !== 'created_at' ? { sort_by: this.sortBy } : {}),
      ...(this.sortDirection && this.sortDirection !== 'desc'
        ? { sort_dir: this.sortDirection as 'asc' | 'desc' }
        : {}),
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

  /** Filters (source/status/window) reset paging, persist, and refetch. */
  onFilterChange(): void {
    this.pageIndex = 0;
    this.syncQueryParams();
    this.load();
  }

  onSearchChange(): void {
    this.search$.next(this.search);
  }

  onPage(event: PageEvent): void {
    this.pageIndex = event.pageIndex;
    this.pageSize = event.pageSize;
    this.syncQueryParams();
    this.load();
  }

  /** MatSort change → map the active column to the backend `sort_by`,
   *  capture the direction, reset to page 0, persist, and refetch. An empty
   *  direction (third click clears the sort) falls back to the default. */
  onSortChange(sort: Sort): void {
    if (sort.direction) {
      this.sortActive = sort.active;
      this.sortDirection = sort.direction;
    } else {
      this.sortActive = 'created_at';
      this.sortDirection = 'desc';
    }
    this.pageIndex = 0;
    this.syncQueryParams();
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
