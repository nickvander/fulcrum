import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule } from '@angular/router';
import { TranslocoModule } from '@ngneat/transloco';
import {
  OrderSource,
  SalesOrderChannelBreakdown,
  SalesOrderSummary,
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
  imports: [CommonModule, RouterModule, MatIconModule, TranslocoModule],
  templateUrl: './sales-by-channel-widget.component.html',
  styleUrl: './sales-by-channel-widget.component.scss',
})
export class SalesByChannelWidgetComponent implements OnChanges {
  @Input() summary: SalesOrderSummary | null = null;

  rows: ChannelRow[] = [];
  hasData = false;

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
}
