import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterModule } from '@angular/router';
import { TranslocoModule } from '@ngneat/transloco';

import { LowStockReport, LowStockRow } from '../../services/low-stock.service';

@Component({
  selector: 'app-low-stock-list',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    RouterModule,
    TranslocoModule,
  ],
  templateUrl: './low-stock-list.component.html',
  styleUrls: ['./low-stock-list.component.scss'],
})
export class LowStockListWidgetComponent {
  @Input() report: LowStockReport | null = null;

  get rows(): LowStockRow[] {
    return this.report?.rows ?? [];
  }

  get summary(): { critical: number; low: number; watch: number } {
    return {
      critical: this.report?.total_critical ?? 0,
      low: this.report?.total_low ?? 0,
      watch: this.report?.total_watch ?? 0,
    };
  }

  daysLeftLabel(row: LowStockRow): string {
    if (!row.daily_velocity || row.daily_velocity <= 0) return '—';
    if (row.days_of_inventory >= 999) return '—';
    return `${row.days_of_inventory.toFixed(1)}d`;
  }

  velocityLabel(row: LowStockRow): string {
    if (!row.daily_velocity || row.daily_velocity <= 0) return '—';
    return `${row.daily_velocity.toFixed(2)}/day`;
  }
}
