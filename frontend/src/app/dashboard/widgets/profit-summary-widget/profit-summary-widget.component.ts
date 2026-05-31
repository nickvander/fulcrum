import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterModule } from '@angular/router';
import { TranslocoModule } from '@ngneat/transloco';
import { finalize } from 'rxjs';

import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import {
  AnalyticsReportsService,
  ProfitPeriod,
  ProfitSummary,
} from '../../services/analytics-reports.service';

/**
 * "¿Gané o perdí?" profit summary — the signature business-bottom-line
 * surface. Combines order-contribution profit and operating expenses into
 * ONE plain-language MXN number for the period.
 *
 * Rendered in two faces from one component:
 *  - `compact` (default false → set true on the dashboard widget): the lead
 *    "signature number" tile at the top of the populated cockpit, with a
 *    "Ver detalle" link to the full page.
 *  - full (page mode): the period selector + the plain breakdown ladder.
 *
 * Brand rules honored: the big number is the hero (display face, tabular,
 * explicit MXN, never animated). A LOSS uses the semantic danger token +
 * a ↓ icon — never chile-red. A PROFIT uses the success token + ↑. Empty
 * state (no realized orders) shows a warm peer line, never a fake $0.
 */
@Component({
  selector: 'app-profit-summary-widget',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    RouterModule,
    TranslocoModule,
    MoneyPipe,
  ],
  templateUrl: './profit-summary-widget.component.html',
  styleUrls: ['./profit-summary-widget.component.scss'],
})
export class ProfitSummaryWidgetComponent implements OnInit {
  /** Compact dashboard-card face (true) vs. full page face (false). */
  @Input() compact = false;

  readonly periods: ProfitPeriod[] = ['this_month', 'last_7d', 'last_30d'];
  period: ProfitPeriod = 'this_month';

  summary: ProfitSummary | null = null;
  loading = false;
  errored = false;

  constructor(private analytics: AnalyticsReportsService) {}

  ngOnInit(): void {
    this.fetch();
  }

  /** Period selector handler — refetches for the chosen span. */
  selectPeriod(period: ProfitPeriod): void {
    if (period === this.period) return;
    this.period = period;
    this.fetch();
  }

  fetch(): void {
    this.loading = true;
    this.errored = false;
    this.analytics
      .profitSummary(this.period)
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: s => (this.summary = s),
        error: () => (this.errored = true),
      });
  }

  /** True only when the period has realized orders — otherwise the empty
   *  state renders instead of a misleading $0. */
  get hasData(): boolean {
    return !!this.summary && this.summary.has_realized_orders;
  }

  /** Translation key for the verdict headline ('won' | 'lost' | 'even'). */
  get verdictKey(): string {
    const v = this.summary?.verdict;
    if (v === 'won') return 'dashboard.profitSummary.verdict.won';
    if (v === 'lost') return 'dashboard.profitSummary.verdict.lost';
    return 'dashboard.profitSummary.verdict.even';
  }

  /** Material icon for the verdict: ↑ profit, ↓ loss, — even. */
  get verdictIcon(): string {
    const v = this.summary?.verdict;
    if (v === 'won') return 'arrow_upward';
    if (v === 'lost') return 'arrow_downward';
    return 'remove';
  }

  /** Token class for the big number. Loss = danger token (never chile-red),
   *  profit = success token, even = neutral. */
  get verdictClass(): string {
    const v = this.summary?.verdict;
    if (v === 'won') return 'result-won';
    if (v === 'lost') return 'result-lost';
    return 'result-even';
  }
}
