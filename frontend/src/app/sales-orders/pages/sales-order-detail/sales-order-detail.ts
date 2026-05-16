import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatCardModule } from '@angular/material/card';
import { TranslocoModule } from '@ngneat/transloco';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import {
  SalesOrderDetail,
  SalesOrdersService,
} from '../../services/sales-orders.service';

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
    TranslocoModule,
  ],
  templateUrl: './sales-order-detail.html',
  styleUrl: './sales-order-detail.scss',
})
export class SalesOrderDetailComponent implements OnInit {
  order$: Observable<SalesOrderDetail | null> = of(null);
  displayedColumns = ['product', 'quantity', 'unit_price', 'subtotal'];

  constructor(
    private route: ActivatedRoute,
    private salesOrders: SalesOrdersService
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (Number.isFinite(id)) {
      this.order$ = this.salesOrders.get(id).pipe(catchError(() => of(null)));
    }
  }

  externalLink(order: SalesOrderDetail): string | null {
    if (!order.external_order_id) return null;
    if (order.source === 'MERCADOLIBRE') {
      return `https://www.mercadolibre.com.mx/ventas/${order.external_order_id}/detalle`;
    }
    return null;
  }
}
