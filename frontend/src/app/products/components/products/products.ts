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
    // Generate fresh identifiers for manual creation
    const newSku = this.productService.generateUniqueSku();
    const newBarcode = this.productService.generateBarcodeFromSku(newSku);
    const newQrValue = `${window.location.origin}/products/view/${newSku}`;

    const newProduct = {
      id: 0,
      name: '',
      sku: newSku,
      description: '',
      default_resale_price: 0,
      cost_price: 0,
      images: [],
      custom_fields: [],
      is_bundle: false,
      barcode_value: newBarcode,
      qrcode_value: newQrValue
    } as Product;

    this.dialog.open(ProductDetailsDialogComponent, {
      width: '1000px',
      maxHeight: '90vh',
      data: { product: newProduct, mode: 'add' }
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
          console.log('[Products] Scanner result:', result);

          // Case 1: User clicked "Edit Existing" on a found product
          if (result.action === 'edit-existing' && result.productId) {
            // Fetch the full product and open in edit mode
            this.productService.getProductById(result.productId).subscribe(product => {
              this.dialog.open(ProductDetailsDialogComponent, {
                width: '1000px',
                maxHeight: '90vh',
                data: { product: product, mode: 'edit' }
              });
            });
            return;
          }

          // Case 2: New product (either AI didn't find match, or user clicked "Create New")
          // Generate fresh identifiers for all new products
          const newSku = this.productService.generateUniqueSku();
          const newBarcode = this.productService.generateBarcodeFromSku(newSku);
          const newQrValue = `${window.location.origin}/products/view/${newSku}`;

          const newProduct = {
            id: 0,
            name: result.name || '',
            sku: newSku,
            description: result.description || '',
            brand: result.brand || '',
            category: result.category || '',
            default_resale_price: 0,
            cost_price: 0,
            images: [],
            custom_fields: [],
            is_bundle: false,
            barcode_value: newBarcode,
            qrcode_value: newQrValue
          } as Product;

          console.log('[Products] Opening dialog with new product:', newProduct);

          // Open Add Dialog with pre-filled data
          this.dialog.open(ProductDetailsDialogComponent, {
            width: '1000px',
            maxHeight: '90vh',
            data: { product: newProduct, mode: 'add' }
          });
        }
      });
    });
  }
}