import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { TranslocoModule } from '@ngneat/transloco';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import {
  OrderSource,
  SalesOrder,
  SalesOrdersService,
} from '../../services/sales-orders.service';

@Component({
  selector: 'app-sales-order-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatTooltipModule,
    MatProgressBarModule,
    MatSelectModule,
    MatFormFieldModule,
    TranslocoModule,
  ],
  templateUrl: './sales-order-list.html',
  styleUrl: './sales-order-list.scss',
})
export class SalesOrderListComponent implements OnInit {
  orders$: Observable<SalesOrder[]> = of([]);
  loading = false;

  source: OrderSource | 'ALL' = 'ALL';
  days = 30;

  displayedColumns = ['created_at', 'source', 'external', 'status', 'total'];

  constructor(private salesOrders: SalesOrdersService) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading = true;
    const opts = {
      ...(this.source !== 'ALL' ? { source: this.source } : {}),
      days: this.days,
      limit: 200,
    };
    this.orders$ = this.salesOrders.list(opts).pipe(
      catchError(() => {
        this.loading = false;
        return of([] as SalesOrder[]);
      })
    );
    this.orders$.subscribe({
      next: () => (this.loading = false),
      error: () => (this.loading = false),
    });
  }

  onSourceChange(): void {
    this.refresh();
  }

  onDaysChange(): void {
    this.refresh();
  }

  sourceChipClass(source: OrderSource | null | undefined): string {
    if (!source) return '';
    return `source-chip ${source.toLowerCase()}`;
  }

  statusChipClass(status: string | null | undefined): string {
    if (!status) return 'status-unknown';
    const lower = status.toLowerCase();
    if (['paid', 'confirmed', 'completed', 'shipped'].includes(lower)) return 'status-good';
    if (['pending', 'processing'].includes(lower)) return 'status-pending';
    if (['cancelled', 'canceled', 'failed', 'refunded'].includes(lower)) return 'status-bad';
    return 'status-unknown';
  }
}
