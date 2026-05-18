import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterModule } from '@angular/router';
import { TranslocoModule } from '@ngneat/transloco';

import { ReportDownloadService } from '../../../core/services/report-download.service';
import {
  OrderSource,
  SalesOrderChannelBreakdown,
  SalesOrderSummary,
  SalesOrdersService,
} from '../../../sales-orders/services/sales-orders.service';

interface ChannelRow {
  source: OrderSource;
  label: string;
  count: number;
  revenue: number;
  share: number;
}

@Component({
  selector: 'app-sales-by-channel-widget',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    TranslocoModule,
  ],
  templateUrl: './sales-by-channel-widget.component.html',
  styleUrl: './sales-by-channel-widget.component.scss',
})
export class SalesByChannelWidgetComponent implements OnChanges {
  @Input() summary: SalesOrderSummary | null = null;
  /** Window size used by the source summary call; mirrored to the export
   *  request so CSV/PDF cover the same date range as the on-screen data. */
  @Input() days = 30;

  rows: ChannelRow[] = [];
  hasData = false;

  constructor(
    private salesOrdersService: SalesOrdersService,
    private reportDownloader: ReportDownloadService,
  ) {}

  ngOnChanges(_: SimpleChanges): void {
    if (!this.summary) {
      this.rows = [];
      this.hasData = false;
      return;
    }
    const labels: Record<OrderSource, string> = {
      MERCADOLIBRE: 'MercadoLibre',
      AMAZON: 'Amazon',
      FULCRUM: 'Fulcrum',
    };
    const totalRevenue = this.summary.total_revenue || 0;
    this.rows = this.summary.by_channel
      .map((row: SalesOrderChannelBreakdown) => ({
        source: row.source,
        label: labels[row.source] ?? row.source,
        count: row.count,
        revenue: row.revenue,
        share: totalRevenue > 0 ? Math.round((row.revenue / totalRevenue) * 100) : 0,
      }))
      .sort((a, b) => b.revenue - a.revenue);
    this.hasData = this.summary.total_orders > 0;
  }

  channelClass(source: OrderSource): string {
    return source.toLowerCase();
  }

  exportCsv(): void {
    this.reportDownloader.download(
      this.salesOrdersService.exportSummaryCsv(this.days),
      'fulcrum-sales-by-channel',
      'csv',
    );
  }

  exportPdf(): void {
    this.reportDownloader.download(
      this.salesOrdersService.exportSummaryPdf(this.days),
      'fulcrum-sales-by-channel',
      'pdf',
    );
  }
}
