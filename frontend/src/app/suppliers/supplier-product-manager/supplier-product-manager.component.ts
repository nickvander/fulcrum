
import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialog } from '@angular/material/dialog';
import { SuppliersService } from '../suppliers.service';
import { SupplierProduct } from '../../shared/models/supplier-product.model';
import { RouterModule, Router } from '@angular/router';

@Component({
  selector: 'app-supplier-product-manager',
  standalone: true,
  imports: [CommonModule, MatTableModule, MatButtonModule, MatIconModule, RouterModule],
  templateUrl: './supplier-product-manager.component.html',
  styleUrls: ['./supplier-product-manager.component.scss'],
  styles: [`
    .product-link {
        color: #1976d2;
        text-decoration: none;
        font-weight: 500;
        cursor: pointer;
    }
    .product-link:hover {
        text-decoration: underline;
    }
`]
})
export class SupplierProductManagerComponent implements OnInit {
  @Input() supplierId!: number;
  supplierProducts: SupplierProduct[] = [];
  displayedColumns: string[] = ['product_name', 'supplier_sku', 'cost_price', 'lead_time_days', 'last_ordered_at'];

  constructor(private suppliersService: SuppliersService, private router: Router) { }

  ngOnInit(): void {
    if (this.supplierId) {
      this.loadProducts();
    }
  }

  loadProducts() {
    this.suppliersService.getSupplierProducts(this.supplierId).subscribe(products => {
      this.supplierProducts = products;
    });
  }

  navigateToProduct(productId: number): void {
    this.router.navigate(['/products/edit', productId]);
  }

  // Placeholder for manual add if needed later
  addProduct() {
    // console.log('Add product dialog');
  }
}
