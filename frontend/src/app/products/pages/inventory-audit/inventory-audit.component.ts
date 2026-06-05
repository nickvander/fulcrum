import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatNativeDateModule } from '@angular/material/core';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { RouterModule } from '@angular/router';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { Subject, takeUntil, debounceTime, distinctUntilChanged } from 'rxjs';

import { ReportDownloadService } from '../../../core/services/report-download.service';
import {
  ConfirmationDialog,
  ConfirmationDialogData,
} from '../../../shared/components/confirmation-dialog/confirmation-dialog';
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
    MatDatepickerModule,
    MatNativeDateModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatPaginatorModule,
    MatProgressBarModule,
    MatSelectModule,
    MatSnackBarModule,
    MatTableModule,
    MatTooltipModule,
    MatDialogModule,
    TranslocoModule,
  ],
  templateUrl: './inventory-audit.component.html',
  styleUrls: ['./inventory-audit.component.scss'],
})
export class InventoryAuditComponent implements OnInit, OnDestroy {
  rows: InventoryAdjustmentRow[] = [];
  total = 0;
  loading = false;
  /** Adjustment id currently being reversed (disables its button). */
  reversingId: number | null = null;
  displayedColumns = ['timestamp', 'product', 'sku', 'adjustment', 'reason_code', 'source', 'reason', 'created_by', 'actions'];

  /** Reason-code dropdown options. Loaded once on init from
   *  `GET /reports/inventory-adjustments/reason-codes` so the
   *  client doesn't hard-code the enum. The `''` option is "all
   *  reasons" and `'none'` is the magic value for legacy
   *  uncategorized (NULL) rows. */
  reasonCodes: string[] = [];

  /** Structured-source dropdown options (P2-8). Loaded once on init
   *  from `GET /reports/inventory-adjustments/sources`. `''` = all,
   *  `'none'` = rows with no structured source (legacy / manual). */
  sources: string[] = [];

  // Filters
  searchProductId: number | null = null;
  startDate: Date | null = null;
  endDate: Date | null = null;
  reasonCode: string = '';
  source: string = '';

  // Pagination
  pageIndex = 0;
  pageSize = 25;
  readonly pageSizeOptions = [10, 25, 50, 100];

  private refresh$ = new Subject<void>();
  private destroy$ = new Subject<void>();

  constructor(
    private auditService: InventoryAuditService,
    private reportDownloader: ReportDownloadService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private transloco: TranslocoService,
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
    // Same for the structured-source dropdown.
    this.auditService
      .listSources()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (sources) => (this.sources = sources),
        error: () => (this.sources = []),
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
      // The backend accepts ISO datetimes; the datepickers give Date objects.
      // Pad to start/end of day so a "from May 1 to May 17" filter is
      // inclusive on both ends.
      after: this.startDate ? `${toIsoDate(this.startDate)}T00:00:00` : null,
      before: this.endDate ? `${toIsoDate(this.endDate)}T23:59:59` : null,
      reasonCode: this.reasonCode || null,
      source: this.source || null,
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
    if (this.searchProductId == null && !this.startDate && !this.endDate && !this.reasonCode && !this.source) return;
    this.searchProductId = null;
    this.startDate = null;
    this.endDate = null;
    this.reasonCode = '';
    this.source = '';
    this.onFilterChange();
  }

  hasActiveFilters(): boolean {
    return this.searchProductId != null || !!this.startDate || !!this.endDate || !!this.reasonCode || !!this.source;
  }

  /**
   * Localized label for a structured source. Known sources resolve to
   * `inventoryAudit.sourceLabel.<source>`; unknown (future backend) keys
   * fall back to a capitalized form so the table never shows a raw enum.
   */
  sourceLabel(source: string): string {
    if (!source) return '';
    if (source === 'none') return this.transloco.translate('inventoryAudit.sourceNone');
    const key = `inventoryAudit.sourceLabel.${source}`;
    const translated = this.transloco.translate(key);
    return translated && translated !== key
      ? translated
      : source.charAt(0).toUpperCase() + source.slice(1);
  }

  /**
   * Human-readable, localized label for a reason code. Known codes resolve to
   * `inventoryAudit.reason.<code>`; unknown (backend-defined) codes fall back to
   * a capitalized form so nothing breaks if the taxonomy grows.
   */
  reasonCodeLabel(code: string): string {
    if (!code) return '';
    if (code === 'none') return this.transloco.translate('inventoryAudit.reasonCodeUncategorized');
    const key = `inventoryAudit.reasonLabel.${code}`;
    const translated = this.transloco.translate(key);
    return translated && translated !== key
      ? translated
      : code.charAt(0).toUpperCase() + code.slice(1);
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

  /** Confirm + reverse an operator adjustment. Books an
   *  equal-and-opposite correction on the server, then reloads the
   *  page so the new row + "reversed" badge appear. */
  reverseRow(row: InventoryAdjustmentRow): void {
    if (!row.reversible || this.reversingId != null) return;

    const data: ConfirmationDialogData = {
      title: this.transloco.translate('inventoryAudit.reverse.confirmTitle'),
      message: this.transloco.translate('inventoryAudit.reverse.confirmMessage', {
        delta: row.adjustment > 0 ? `+${row.adjustment}` : row.adjustment,
        product: row.product_name || (row.product_sku ?? `#${row.product_id}`),
      }),
    };
    this.dialog
      .open(ConfirmationDialog, { data, width: '420px', autoFocus: false })
      .afterClosed()
      .subscribe((confirmed) => {
        if (!confirmed) return;
        this.reversingId = row.id;
        this.auditService
          .reverse(row.id)
          .pipe(takeUntil(this.destroy$))
          .subscribe({
            next: () => {
              this.reversingId = null;
              this.snackBar.open(
                this.transloco.translate('inventoryAudit.reverse.savedSnackbar'),
                this.transloco.translate('common.close'),
                { duration: 4000 },
              );
              this.loadPage();
            },
            error: () => {
              this.reversingId = null;
              this.snackBar.open(
                this.transloco.translate('inventoryAudit.reverse.error'),
                this.transloco.translate('common.close'),
                { duration: 5000 },
              );
            },
          });
      });
  }
}

/** Format a Date as a local-time YYYY-MM-DD string. We deliberately use the
 *  local calendar date (not toISOString, which is UTC) so the value matches
 *  what the operator picked and what the backend's date parser expects. */
function toIsoDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}
