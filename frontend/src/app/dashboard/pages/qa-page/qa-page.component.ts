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
  QuestionRow,
  QuestionsListResponse,
} from '../../services/analytics-reports.service';

/**
 * Buyer Q&A drill-down page (`/reports/qa`).
 *
 * One row per buyer question pulled from the marketplace, newest first,
 * with a response-time SLA badge (answered / pending / breached). Mirrors
 * the returns page so operators keep the same UI mental model. The
 * headline counters surface "how many am I behind on" at a glance.
 */
@Component({
  selector: 'app-qa-page',
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
  templateUrl: './qa-page.component.html',
  styleUrls: ['./qa-page.component.scss'],
})
export class QaPageComponent implements OnInit {
  windowDays: 30 | 60 | 90 | 180 = 30;
  /** '' = all, else 'unanswered' | 'answered'. */
  statusFilter: '' | 'unanswered' | 'answered' = '';

  pageIndex = 0;
  pageSize = 50;
  totalRows = 0;

  rows: QuestionRow[] = [];
  unansweredCount = 0;
  breachedCount = 0;
  answeredCount = 0;
  slaHours = 24;
  loading = false;
  errored = false;

  readonly displayedColumns = [
    'asked_at',
    'source',
    'item',
    'question',
    'sla',
    'hours_open',
  ];

  readonly windowOptions: Array<{ value: 30 | 60 | 90 | 180; labelKey: string }> = [
    { value: 30, labelKey: 'dashboard.qaPage.window30' },
    { value: 60, labelKey: 'dashboard.qaPage.window60' },
    { value: 90, labelKey: 'dashboard.qaPage.window90' },
    { value: 180, labelKey: 'dashboard.qaPage.window180' },
  ];

  readonly statusOptions: Array<{ value: '' | 'unanswered' | 'answered'; labelKey: string }> = [
    { value: '', labelKey: 'dashboard.qaPage.statusAll' },
    { value: 'unanswered', labelKey: 'dashboard.qaPage.statusUnanswered' },
    { value: 'answered', labelKey: 'dashboard.qaPage.statusAnswered' },
  ];

  constructor(private analytics: AnalyticsReportsService) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.errored = false;
    const skip = this.pageIndex * this.pageSize;
    const statusParam = this.statusFilter === '' ? undefined : this.statusFilter;
    this.analytics
      .questionsList(this.windowDays, skip, this.pageSize, statusParam)
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: (resp: QuestionsListResponse) => {
          this.rows = resp.rows;
          this.totalRows = resp.total;
          this.unansweredCount = resp.unanswered_count;
          this.breachedCount = resp.breached_count;
          this.answeredCount = resp.answered_count;
          this.slaHours = resp.sla_hours;
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

  channelLabel(source: string | null): string {
    if (source === 'MERCADOLIBRE') return 'MercadoLibre';
    if (source === 'AMAZON') return 'Amazon';
    return source || '—';
  }

  /** Pill colour for the SLA badge. */
  slaClass(sla: string): string {
    if (sla === 'breached') return 'sla-breached';
    if (sla === 'answered') return 'sla-answered';
    return 'sla-pending';
  }

  /** Compact "Xh" / "Xd" from an hours value. */
  hoursLabel(hours: number | null): string {
    if (hours == null) return '—';
    if (hours < 24) return `${Math.round(hours)}h`;
    return `${Math.round(hours / 24)}d`;
  }
}
