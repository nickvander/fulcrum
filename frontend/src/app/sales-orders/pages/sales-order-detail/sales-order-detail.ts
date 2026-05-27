import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { Observable, of } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import {
  SalesOrderDetail,
  SalesOrderReturn,
  SalesOrdersService,
} from '../../services/sales-orders.service';
import {
  RecordReturnDialogComponent,
  RecordReturnDialogData,
} from '../../components/record-return-dialog/record-return-dialog.component';

@Component({
  selector: 'app-sales-order-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatCardModule,
    MatDialogModule,
    MatSnackBarModule,
    TranslocoModule,
  ],
  templateUrl: './sales-order-detail.html',
  styleUrl: './sales-order-detail.scss',
})
export class SalesOrderDetailComponent implements OnInit {
  order: SalesOrderDetail | null = null;
  loading = true;
  order$: Observable<SalesOrderDetail | null> = of(null);
  returns: SalesOrderReturn[] = [];
  loadingReturns = false;
  displayedColumns = ['product', 'quantity', 'unit_price', 'subtotal'];

  constructor(
    private route: ActivatedRoute,
    private salesOrders: SalesOrdersService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private transloco: TranslocoService,
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (Number.isFinite(id)) {
      this.order$ = this.salesOrders.get(id).pipe(
        tap((order) => {
          this.order = order;
          this.loading = false;
          // Defer the returns load until after the order is in
          // hand — the page can render the header + items
          // immediately while returns trickle in.
          this.loadReturns(id);
        }),
        catchError(() => {
          this.loading = false;
          return of(null);
        }),
      );
    }
  }

  externalLink(order: SalesOrderDetail): string | null {
    if (!order.external_order_id) return null;
    if (order.source === 'MERCADOLIBRE') {
      return `https://www.mercadolibre.com.mx/ventas/${order.external_order_id}/detalle`;
    }
    return null;
  }

  /** Fetch the history of recorded return events for this order. */
  private loadReturns(orderId: number): void {
    this.loadingReturns = true;
    this.salesOrders.listReturns(orderId).subscribe({
      next: (rows) => {
        this.returns = rows;
        this.loadingReturns = false;
      },
      error: () => {
        // Non-fatal: the rest of the page still works. We just
        // don't show the history. A snackbar would be noisy for a
        // page that the operator might rarely reach.
        this.returns = [];
        this.loadingReturns = false;
      },
    });
  }

  /** Open the record-return dialog. Disabled when the order has no
   *  line items (nothing to return). On success the dialog returns
   *  the created rows so we can prepend them locally. */
  openRecordReturnDialog(): void {
    if (!this.order) return;
    const ref = this.dialog.open(RecordReturnDialogComponent, {
      data: { order: this.order } as RecordReturnDialogData,
      width: '640px',
      autoFocus: false,
    });
    ref.afterClosed().subscribe((result) => {
      if (!result || !result.created || !this.order) return;
      // Newest-first: prepend the created rows.
      this.returns = [...result.created, ...this.returns];
      this.snackBar.open(
        this.transloco.translate('orders.recordReturn.savedSnackbar', {
          n: result.created.length,
        }),
        this.transloco.translate('common.close'),
        { duration: 4000 },
      );
    });
  }
}
