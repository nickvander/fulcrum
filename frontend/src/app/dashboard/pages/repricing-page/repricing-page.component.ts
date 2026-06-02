import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { finalize } from 'rxjs';

import {
  AnalyticsReportsService,
  RepricingReport,
  RepricingRow,
} from '../../services/analytics-reports.service';

/**
 * Repricing assistant page (`/reports/repricing`).
 *
 * Surfaces listings priced below a target net-margin floor — computed from
 * real COGS + the effective fee/shipping rate (settled finance data when
 * available, else the marketplace default). Each row offers a one-click
 * "Apply" that pushes the suggested price to the marketplace via the
 * existing connector `sync_price`. A 409 `needs_reauthorization` flips the
 * row into a Reconnect state, mirroring the Q&A inbox.
 *
 * v1 is margin-floor only — a competitor / buy-box signal is deferred.
 */
@Component({
  selector: 'app-repricing-page',
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
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSnackBarModule,
    MatTableModule,
    MatTooltipModule,
    TranslocoModule,
  ],
  templateUrl: './repricing-page.component.html',
  styleUrls: ['./repricing-page.component.scss'],
})
export class RepricingPageComponent implements OnInit {
  marginFloorPercent: 5 | 10 | 15 | 20 = 10;

  rows: RepricingRow[] = [];
  totalLoss = 0;
  totalBelowFloor = 0;
  loading = false;
  errored = false;

  /** listing_id currently being pushed. */
  applyingId: number | null = null;
  /** listing_id whose apply needs marketplace reauthorization. */
  reauthId: number | null = null;
  /** listing_id whose apply hit a generic error. */
  applyErrorId: number | null = null;

  readonly displayedColumns = [
    'product',
    'marketplace',
    'status',
    'current',
    'suggested',
    'actions',
  ];

  readonly floorOptions: Array<{ value: 5 | 10 | 15 | 20; labelKey: string }> = [
    { value: 5, labelKey: 'dashboard.repricingPage.floor5' },
    { value: 10, labelKey: 'dashboard.repricingPage.floor10' },
    { value: 15, labelKey: 'dashboard.repricingPage.floor15' },
    { value: 20, labelKey: 'dashboard.repricingPage.floor20' },
  ];

  constructor(
    private analytics: AnalyticsReportsService,
    private snackBar: MatSnackBar,
    private transloco: TranslocoService,
  ) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.errored = false;
    this.reauthId = null;
    this.applyErrorId = null;
    this.analytics
      .repricing(this.marginFloorPercent)
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: (resp: RepricingReport) => {
          this.rows = resp.rows;
          this.totalLoss = resp.total_loss;
          this.totalBelowFloor = resp.total_below_floor;
        },
        error: () => {
          this.errored = true;
          this.rows = [];
          this.totalLoss = 0;
          this.totalBelowFloor = 0;
        },
      });
  }

  onFilterChange(): void {
    this.load();
  }

  /** Push the suggested price to the marketplace for one row. */
  apply(row: RepricingRow): void {
    if (row.suggested_price == null || this.applyingId !== null) return;
    this.applyingId = row.listing_id;
    this.reauthId = null;
    this.applyErrorId = null;
    const price = row.suggested_price;
    this.analytics
      .applyPrice(row.listing_id, price)
      .pipe(finalize(() => (this.applyingId = null)))
      .subscribe({
        next: () => {
          // The row now clears the floor — drop it from the at-risk list.
          this.rows = this.rows.filter((r) => r.listing_id !== row.listing_id);
          this.recountTotals();
          this.snackBar.open(
            this.transloco.translate('dashboard.repricingPage.applySuccess'),
            undefined,
            { duration: 2500 },
          );
        },
        error: (err: HttpErrorResponse) => {
          const code = err?.error?.code;
          if (err?.status === 409 && code === 'needs_reauthorization') {
            this.reauthId = row.listing_id;
          } else {
            this.applyErrorId = row.listing_id;
          }
        },
      });
  }

  private recountTotals(): void {
    this.totalLoss = this.rows.filter((r) => r.status === 'loss').length;
    this.totalBelowFloor = this.rows.filter(
      (r) => r.status === 'loss' || r.status === 'below_floor',
    ).length;
  }

  formatCurrency(value: number): string {
    return value.toLocaleString('en-US', {
      style: 'currency', currency: 'MXN', maximumFractionDigits: 2,
    });
  }
}
