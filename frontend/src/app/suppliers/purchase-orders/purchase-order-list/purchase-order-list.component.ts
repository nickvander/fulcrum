import { Component, OnInit } from '@angular/core';
import { PurchaseOrder } from '../../../shared/models/purchase-order.model';
import { SuppliersService } from '../../suppliers.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-purchase-order-list',
  templateUrl: './purchase-order-list.component.html',
  styleUrls: ['./purchase-order-list.component.scss'],
  standalone: false
})
export class PurchaseOrderListComponent implements OnInit {
  purchaseOrders: PurchaseOrder[] = [];
  displayedColumns: string[] = ['id', 'supplier', 'status', 'total', 'created_at', 'actions'];

  constructor(
    private suppliersService: SuppliersService,
    private router: Router
  ) { }

  ngOnInit(): void {
    this.loadPurchaseOrders();
  }

  loadPurchaseOrders(): void {
    this.suppliersService.getPurchaseOrders().subscribe(pos => {
      this.purchaseOrders = pos;
    });
  }

  createPurchaseOrder(): void {
    this.router.navigate(['/suppliers/po/create']);
  }

  viewDetail(id: number): void {
    this.router.navigate(['/suppliers/po', id]);
  }

  createSupplier(): void {
    this.router.navigate(['/suppliers/id/new']);
  }
}
