import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule } from '@ngneat/transloco';
import { finalize } from 'rxjs';

import {
  AnalyticsReportsService,
  ReplenishmentReport,
  ReplenishmentRow,
} from '../../services/analytics-reports.service';
import { ReportDownloadService } from '../../../core/services/report-download.service';

/**
 * Replenishment-to-Full planner page (`/reports/replenishment`).
 *
 * The "when" the low-stock report lacks: for each SKU selling on
 * MercadoLibre, the two dated actions that keep ML Full stocked —
 * **send internal stock to Full by** date Y and **reorder from the
 * supplier by** date X (using `SupplierProduct.lead_time_days`).
 * Velocity is ML-channel-scoped, matching the `ml_full_stockout_risk`
 * alert, so the alert and this plan agree on the numbers.
 *
 * Actions deep-link to the existing surfaces that execute them: the
 * Send-to-Full transfer planner and the supplier PO flow.
 */
@Component({
  selector: 'app-replenishment-page',
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
    MatTableModule,
    MatTooltipModule,
    TranslocoModule,
  ],
  templateUrl: './replenishment-page.component.html',
  styleUrls: ['./replenishment-page.component.scss'],
})
export class ReplenishmentPageComponent implements OnInit {
  velocityWindowDays: 14 | 30 | 60 | 90 = 30;
  fullTransferLeadDays = 14;
  targetCoverDays = 30;

  rows: ReplenishmentRow[] = [];
  totalSendNow = 0;
  totalReorderNow = 0;
  loading = false;
  errored = false;

  readonly displayedColumns = [
    'product',
    'severity',
    'velocity',
    'stock',
    'send',
    'reorder',
  ];

  readonly windowOptions: Array<{ value: 14 | 30 | 60 | 90; labelKey: string }> = [
    { value: 14, labelKey: 'dashboard.replenishmentPage.window14' },
    { value: 30, labelKey: 'dashboard.replenishmentPage.window30' },
    { value: 60, labelKey: 'dashboard.replenishmentPage.window60' },
    { value: 90, labelKey: 'dashboard.replenishmentPage.window90' },
  ];

  readonly leadOptions = [7, 14, 21, 30];
  readonly coverOptions = [14, 30, 45, 60];

  constructor(
    private analytics: AnalyticsReportsService,
    private downloader: ReportDownloadService,
  ) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.errored = false;
    this.analytics
      .replenishment(this.velocityWindowDays, this.fullTransferLeadDays, this.targetCoverDays)
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: (resp: ReplenishmentReport) => {
          this.rows = resp.rows;
          this.totalSendNow = resp.total_send_now;
          this.totalReorderNow = resp.total_reorder_now;
        },
        error: () => {
          this.errored = true;
          this.rows = [];
          this.totalSendNow = 0;
          this.totalReorderNow = 0;
        },
      });
  }

  onFilterChange(): void {
    this.load();
  }

  exportCsv(): void {
    this.downloader.download(
      this.analytics.exportReplenishmentCsv(
        this.velocityWindowDays, this.fullTransferLeadDays, this.targetCoverDays,
      ),
      'fulcrum-replenishment',
      'csv',
    );
  }

  exportPdf(): void {
    this.downloader.download(
      this.analytics.exportReplenishmentPdf(
        this.velocityWindowDays, this.fullTransferLeadDays, this.targetCoverDays,
      ),
      'fulcrum-replenishment',
      'pdf',
    );
  }

  /** True when a date is today or in the past (action is due now). */
  isDue(isoDate: string | null): boolean {
    if (!isoDate) return false;
    const today = new Date().toISOString().slice(0, 10);
    return isoDate <= today;
  }
}
