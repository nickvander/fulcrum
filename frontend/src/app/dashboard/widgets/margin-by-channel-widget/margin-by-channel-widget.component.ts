import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule } from '@ngneat/transloco';
import { finalize } from 'rxjs';

import {
  AnalyticsReportsService,
  CostRollupByChannelResponse,
  CostRollupByChannelRow,
} from '../../services/analytics-reports.service';

/**
 * "Margin by channel" stacked bar — one horizontal stack per
 * marketplace showing COGS / fees / shipping / ad spend / profit
 * proportions. Hand-rolled CSS flexbox (no chart library
 * dependency) so the build stays light and the math is easy to
 * test.
 */
@Component({
  selector: 'app-margin-by-channel-widget',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    TranslocoModule,
  ],
  templateUrl: './margin-by-channel-widget.component.html',
  styleUrls: ['./margin-by-channel-widget.component.scss'],
})
export class MarginByChannelWidgetComponent implements OnInit {
  data: CostRollupByChannelResponse | null = null;
  loading = false;
  errored = false;
  windowDays = 30;

  constructor(private analytics: AnalyticsReportsService) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading = true;
    this.errored = false;
    this.analytics.costRollupByChannel(this.windowDays)
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: r => (this.data = r),
        error: () => (this.errored = true),
      });
  }

  /**
   * Compute the percentage each cost component contributes to a
   * channel's revenue. Loss-making channels (total_cost > revenue)
   * produce a "loss" segment instead of profit so the bar always
   * sums to 100% of revenue and the operator sees the overrun
   * visually.
   */
  segments(row: CostRollupByChannelRow): Array<{ kind: string; pct: number; amount: number }> {
    const revenue = row.revenue_amount_mxn || 0;
    if (revenue <= 0) return [];
    const cogs = Math.max(0, row.cogs_amount || 0);
    const fees = Math.max(0, row.marketplace_fees_amount || 0);
    const shipping = Math.max(0, row.shipping_cost_amount || 0);
    const ads = Math.max(0, row.ad_spend_amount || 0);
    const other = Math.max(0, row.other_cost_amount || 0);
    const totalCost = cogs + fees + shipping + ads + other;
    const segs: Array<{ kind: string; pct: number; amount: number }> = [];
    const push = (kind: string, amount: number) => {
      if (amount > 0) segs.push({ kind, pct: (amount / revenue) * 100, amount });
    };
    push('cogs', cogs);
    push('fees', fees);
    push('shipping', shipping);
    push('ads', ads);
    push('other', other);
    if (totalCost >= revenue) {
      // Loss-making — flag the overrun explicitly.
      push('loss', totalCost - revenue);
    } else {
      push('profit', revenue - totalCost);
    }
    return segs;
  }

  formatCurrency(value: number | null | undefined): string {
    if (value === null || value === undefined) return '—';
    return value.toLocaleString('en-US', {
      style: 'currency', currency: 'MXN', maximumFractionDigits: 0,
    });
  }

  formatMargin(value: number | null | undefined): string {
    if (value === null || value === undefined) return '—';
    return `${value.toFixed(1)}%`;
  }
}
