import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterModule } from '@angular/router';
import { TranslocoModule } from '@ngneat/transloco';
import { Subject, takeUntil, debounceTime, distinctUntilChanged } from 'rxjs';

import { ReportDownloadService } from '../../../core/services/report-download.service';
import {
  InventoryAdjustmentRow,
  InventoryAuditFilters,
  InventoryAuditService,
} from '../../services/inventory-audit.service';

@Component({
  selector: 'app-inventory-audit',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatPaginatorModule,
    MatProgressBarModule,
    MatSelectModule,
    MatTableModule,
    MatTooltipModule,
    TranslocoModule,
  ],
  templateUrl: './inventory-audit.component.html',
  styleUrls: ['./inventory-audit.component.scss'],
})
export class InventoryAuditComponent implements OnInit, OnDestroy {
  rows: InventoryAdjustmentRow[] = [];
  total = 0;
  loading = false;
  displayedColumns = ['timestamp', 'product', 'sku', 'adjustment', 'reason_code', 'reason', 'created_by'];

  /** Reason-code dropdown options. Loaded once on init from
   *  `GET /reports/inventory-adjustments/reason-codes` so the
   *  client doesn't hard-code the enum. The `''` option is "all
   *  reasons" and `'none'` is the magic value for legacy
   *  uncategorized (NULL) rows. */
  reasonCodes: string[] = [];

  // Filters
  searchProductId: number | null = null;
  startDate: string = '';  // YYYY-MM-DD
  endDate: string = '';
  reasonCode: string = '';

  // Pagination
  pageIndex = 0;
  pageSize = 25;
  readonly pageSizeOptions = [10, 25, 50, 100];

  private refresh$ = new Subject<void>();
  private destroy$ = new Subject<void>();

  constructor(
    private auditService: InventoryAuditService,
    private reportDownloader: ReportDownloadService,
  ) {}

  ngOnInit(): void {
    this.refresh$
      .pipe(debounceTime(150), distinctUntilChanged((a, b) => false), takeUntil(this.destroy$))
      .subscribe(() => this.loadPage());
    // Fetch the canonical reason-code list for the dropdown. Failure
    // is benign — without the list the dropdown stays empty and the
    // operator can still browse the unfiltered audit.
    this.auditService
      .listReasonCodes()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (codes) => (this.reasonCodes = codes),
        error: () => (this.reasonCodes = []),
      });
    this.loadPage();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /** Build the filter shape for both list + export so they stay in sync. */
  private filters(): InventoryAuditFilters {
    return {
      productId: this.searchProductId ?? null,
      // The backend accepts ISO datetimes; the date inputs give YYYY-MM-DD.
      // Pad to start/end of day so a "from May 1 to May 17" filter is
      // inclusive on both ends.
      after: this.startDate ? `${this.startDate}T00:00:00` : null,
      before: this.endDate ? `${this.endDate}T23:59:59` : null,
      reasonCode: this.reasonCode || null,
    };
  }

  loadPage(): void {
    this.loading = true;
    this.auditService
      .list({
        ...this.filters(),
        skip: this.pageIndex * this.pageSize,
        limit: this.pageSize,
      })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (resp) => {
          this.rows = resp.rows;
          this.total = resp.total;
          this.loading = false;
        },
        error: () => {
          this.loading = false;
        },
      });
  }

  onFilterChange(): void {
    this.pageIndex = 0;
    this.refresh$.next();
  }

  onPage(event: PageEvent): void {
    this.pageIndex = event.pageIndex;
    this.pageSize = event.pageSize;
    this.loadPage();
  }

  clearFilters(): void {
    if (this.searchProductId == null && !this.startDate && !this.endDate && !this.reasonCode) return;
    this.searchProductId = null;
    this.startDate = '';
    this.endDate = '';
    this.reasonCode = '';
    this.onFilterChange();
  }

  hasActiveFilters(): boolean {
    return this.searchProductId != null || !!this.startDate || !!this.endDate || !!this.reasonCode;
  }

  /** Human-readable label for a reason code. The codes are
   *  lowercase enum values; we capitalize for display without
   *  routing through a full per-code i18n key. */
  reasonCodeLabel(code: string): string {
    if (!code) return '';
    if (code === 'none') return 'Uncategorized';
    return code.charAt(0).toUpperCase() + code.slice(1);
  }

  exportCsv(): void {
    this.reportDownloader.download(
      this.auditService.exportCsv(this.filters()),
      'fulcrum-inventory-adjustments',
      'csv',
    );
  }

  exportPdf(): void {
    this.reportDownloader.download(
      this.auditService.exportPdf(this.filters()),
      'fulcrum-inventory-adjustments',
      'pdf',
    );
  }

  /** UI helper: red text for negative deltas (write-offs), green for positive. */
  deltaClass(delta: number): string {
    if (delta > 0) return 'delta-positive';
    if (delta < 0) return 'delta-negative';
    return '';
  }
}
