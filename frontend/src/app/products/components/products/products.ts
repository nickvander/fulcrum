import { Component, OnInit } from '@angular/core';
import { Product } from '../../models/product.model';
import { ProductService } from '../../services/product';
import { ProductList } from '../product-list/product-list';

import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { ProductDetailsDialogComponent } from '../product-details-dialog/product-details-dialog.component';

@Component({
  selector: 'app-products',
  templateUrl: './products.html',
  styleUrls: ['./products.scss'],
  standalone: true,
  imports: [
    MatButtonModule,
    MatIconModule,
    MatDialogModule,
    ProductList
  ]
})
export class ProductsComponent implements OnInit {
  constructor(
    private productService: ProductService,
    private dialog: MatDialog
  ) { }

  ngOnInit(): void {
  }

  openAddPanel(): void {
    const newProduct = {
      id: 0,
      name: '',
      sku: '',
      description: '',
      default_resale_price: 0,
      cost_price: 0,
      images: [],
      custom_fields: [],
      is_bundle: false
    } as Product;

    this.dialog.open(ProductDetailsDialogComponent, {
      width: '1000px',
      maxHeight: '90vh',
      data: { product: newProduct, mode: 'create' }
    });
  }

  openScanner(): void {
    import('../product-scanner/product-scanner.component').then(({ ProductScannerComponent }) => {
      const dialogRef = this.dialog.open(ProductScannerComponent, {
        width: '600px',
        height: 'auto',
        panelClass: 'scanner-dialog'
      });

      dialogRef.afterClosed().subscribe(result => {
        if (result) {
          // Case 1: Existing Product Found
          if (result.foundProduct) {
            this.dialog.open(ProductDetailsDialogComponent, {
              width: '1000px',
              maxHeight: '90vh',
              data: { product: result.foundProduct, mode: 'edit' }
            });
            return;
          }

          // Case 2: New / Not Found
          const newProduct = {
            id: 0,
            name: result.name || '',
            sku: result.sku || '',
            description: result.description || '',
            brand: result.brand || '',
            category: result.category || '',
            default_resale_price: 0,
            cost_price: 0,
            images: [],
            custom_fields: [],
            is_bundle: false,
            barcode_value: result.barcode
          } as Product;

          // Open Add Dialog with pre-filled data
          this.dialog.open(ProductDetailsDialogComponent, {
            width: '1000px',
            maxHeight: '90vh',
            data: { product: newProduct, mode: 'create' }
          });
        }
      });
    });
  }
}