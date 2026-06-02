import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule } from '@ngneat/transloco';
import { finalize } from 'rxjs';

import {
  CfdiService,
  CfdiOrderRow,
  CfdiReport,
} from '../../../core/services/cfdi.service';
import { ReportDownloadService } from '../../../core/services/report-download.service';

/**
 * CFDI factura export page (`/reports/cfdi`), export-only.
 *
 * Lists realized sales in a CFDI 4.0-ready shape (público-general) and
 * exports them as CSV for an accountant / PAC to timbrar. Warns when the
 * issuer (emisor) RFC isn't configured yet, linking to Settings → CFDI.
 * Per-buyer specific-RFC capture + timbrado are deferred.
 */
@Component({
  selector: 'app-cfdi-page',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTableModule,
    MatTooltipModule,
    TranslocoModule,
  ],
  templateUrl: './cfdi-page.component.html',
  styleUrls: ['./cfdi-page.component.scss'],
})
export class CfdiPageComponent implements OnInit {
  windowDays: 30 | 60 | 90 = 30;

  rows: CfdiOrderRow[] = [];
  issuerConfigured = false;
  orderCount = 0;
  subtotal = 0;
  ivaAmount = 0;
  total = 0;
  loading = false;
  errored = false;

  readonly displayedColumns = [
    'issued_at',
    'external_order_id',
    'receiver',
    'subtotal',
    'iva',
    'total',
  ];

  readonly windowOptions: Array<{ value: 30 | 60 | 90; labelKey: string }> = [
    { value: 30, labelKey: 'dashboard.cfdiPage.window30' },
    { value: 60, labelKey: 'dashboard.cfdiPage.window60' },
    { value: 90, labelKey: 'dashboard.cfdiPage.window90' },
  ];

  constructor(
    private cfdi: CfdiService,
    private downloader: ReportDownloadService,
  ) {}

  ngOnInit(): void {
    this.load();
  }

  private range(): { startDate: string; endDate: string } {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - this.windowDays);
    return {
      startDate: start.toISOString().slice(0, 10),
      endDate: end.toISOString().slice(0, 10),
    };
  }

  load(): void {
    this.loading = true;
    this.errored = false;
    this.cfdi
      .report(this.range())
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: (resp: CfdiReport) => {
          this.rows = resp.rows;
          this.issuerConfigured = resp.issuer.is_configured;
          this.orderCount = resp.order_count;
          this.subtotal = resp.subtotal;
          this.ivaAmount = resp.iva_amount;
          this.total = resp.total;
        },
        error: () => {
          this.errored = true;
          this.rows = [];
          this.orderCount = 0;
        },
      });
  }

  onFilterChange(): void {
    this.load();
  }

  exportCsv(): void {
    this.downloader.download(this.cfdi.exportCsv(this.range()), 'fulcrum-cfdi', 'csv');
  }

  formatCurrency(value: number): string {
    return value.toLocaleString('en-US', {
      style: 'currency', currency: 'MXN', maximumFractionDigits: 2,
    });
  }
}
