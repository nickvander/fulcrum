import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { TranslocoModule } from '@ngneat/transloco';

import {
  AnalyticsReportsService,
  DateRange,
} from '../../services/analytics-reports.service';
import { ReportDownloadService } from '../../../core/services/report-download.service';

type ReportKey = 'velocity' | 'margin' | 'stockout';

/**
 * Compact dashboard card that exposes the velocity / margin / stockout
 * report exports. The reports themselves are CSV/PDF only on the
 * backend (no JSON list endpoint), so this widget intentionally has no
 * on-screen data — it's a download-launcher.
 *
 * The window-days selector applies to all three rows. Velocity and
 * margin use it directly; stockout uses it as the velocity window for
 * its imminent/watch projections (the imminent/watch day caps stay at
 * the backend defaults, 7d / 14d, which match the buyer's typical
 * reorder cycle).
 */
@Component({
  selector: 'app-analytics-reports-widget',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatIconModule,
    MatSelectModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatInputModule,
    MatDatepickerModule,
    MatNativeDateModule,
    TranslocoModule,
  ],
  templateUrl: './analytics-reports-widget.component.html',
  styleUrl: './analytics-reports-widget.component.scss',
})
export class AnalyticsReportsWidgetComponent {
  windowDays: 30 | 60 | 90 | 180 = 30;
  /** Optional explicit date range. When set, overrides windowDays. Both
   *  pickers are independent — partial ranges (start only / end only)
   *  are valid and the backend fills in the missing bound. */
  startDate: Date | null = null;
  endDate: Date | null = null;

  /** Per-row busy flag so a click only disables the row that's actually
   *  downloading, not the whole widget. Indexed by `<reportKey>:<ext>`
   *  to keep CSV and PDF independent. */
  busy = new Set<string>();

  readonly windowOptions: Array<{ value: 30 | 60 | 90 | 180; labelKey: string }> = [
    { value: 30,  labelKey: 'dashboard.analyticsReports.window30' },
    { value: 60,  labelKey: 'dashboard.analyticsReports.window60' },
    { value: 90,  labelKey: 'dashboard.analyticsReports.window90' },
    { value: 180, labelKey: 'dashboard.analyticsReports.window180' },
  ];

  constructor(
    private analyticsReports: AnalyticsReportsService,
    private reportDownloader: ReportDownloadService,
  ) {}

  isBusy(report: ReportKey, ext: 'csv' | 'pdf'): boolean {
    return this.busy.has(`${report}:${ext}`);
  }

  download(report: ReportKey, ext: 'csv' | 'pdf'): void {
    const key = `${report}:${ext}`;
    if (this.busy.has(key)) return;
    this.busy.add(key);

    const stem = this.stemFor(report);
    const blob$ = this.requestFor(report, ext);

    // ReportDownloadService.download() doesn't return an Observable, so
    // we wrap it with our own busy-flag teardown via a tap-style
    // wrapper. Simpler: clear the flag after a short delay matched to
    // typical backend response time; the user only sees the busy state
    // long enough to know the click registered.
    this.reportDownloader.download(blob$, stem, ext);
    // Match the ReportDownloadService promise timing — once the blob is
    // resolved the anchor click fires synchronously. Clear after a
    // short tick so re-clicks are allowed.
    setTimeout(() => this.busy.delete(key), 1500);
  }

  private stemFor(report: ReportKey): string {
    switch (report) {
      case 'velocity': return 'fulcrum-velocity';
      case 'margin':   return 'fulcrum-margin';
      case 'stockout': return 'fulcrum-stockout';
    }
  }

  private requestFor(report: ReportKey, ext: 'csv' | 'pdf') {
    const range = this.currentRange();
    if (report === 'velocity') {
      return ext === 'csv'
        ? this.analyticsReports.exportVelocityCsv(this.windowDays, 2000, range)
        : this.analyticsReports.exportVelocityPdf(this.windowDays, 2000, range);
    }
    if (report === 'margin') {
      return ext === 'csv'
        ? this.analyticsReports.exportMarginCsv(this.windowDays, 2000, range)
        : this.analyticsReports.exportMarginPdf(this.windowDays, 2000, range);
    }
    return ext === 'csv'
      ? this.analyticsReports.exportStockoutCsv(this.windowDays, 7, 14, 2000, range)
      : this.analyticsReports.exportStockoutPdf(this.windowDays, 7, 14, 2000, range);
  }

  /** True when at least one date picker has a value — operators that
   *  haven't touched the pickers fall back to the windowDays selector. */
  hasExplicitRange(): boolean {
    return this.startDate !== null || this.endDate !== null;
  }

  /** True when both pickers are set in the wrong order. Disables the
   *  download buttons + drives a localized hint without burning a
   *  backend round-trip. */
  rangeInverted(): boolean {
    if (!this.startDate || !this.endDate) return false;
    return this.startDate.getTime() > this.endDate.getTime();
  }

  clearRange(): void {
    this.startDate = null;
    this.endDate = null;
  }

  private currentRange(): DateRange | undefined {
    if (!this.hasExplicitRange()) return undefined;
    return {
      startDate: this.startDate ? toIsoDate(this.startDate) : null,
      endDate: this.endDate ? toIsoDate(this.endDate) : null,
    };
  }
}

/** Format a JS Date as `YYYY-MM-DD` in local time — matches what the
 *  backend's `date.fromisoformat` expects and what the operator sees in
 *  the picker. */
function toIsoDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}
