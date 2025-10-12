import { Component, OnInit, OnDestroy } from '@angular/core';
import { ProductService } from '../../services/product';
import { Product } from '../../models/product.model';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { SharedModule } from '../../../shared/shared-module';
import { RouterModule } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { ConfirmationDialog } from '../../../shared/components/confirmation-dialog/confirmation-dialog';
import { Subject, takeUntil } from 'rxjs';
import { MatCardModule } from '@angular/material/card';

import { StockAdjustmentDialog } from '../stock-adjustment-dialog/stock-adjustment-dialog';

@Component({
  selector: 'app-product-list',
  templateUrl: './product-list.html',
  styleUrls: ['./product-list.scss'],
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    SharedModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
  ],
})
export class ProductList implements OnInit, OnDestroy {
  products: Product[] = [];
  private destroy$ = new Subject<void>();

  constructor(
    private productService: ProductService,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.productService.products$
      .pipe(takeUntil(this.destroy$))
      .subscribe((products) => {
        this.products = products;
      });
    this.productService.getProducts().subscribe();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  deleteProduct(id: number): void {
    const dialogRef = this.dialog.open(ConfirmationDialog, {
      data: {
        title: 'Delete Product',
        message: 'Are you sure you want to delete this product? This action cannot be undone.',
      },
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.productService.deleteProduct(id).subscribe();
      }
    });
  }

  openStockAdjustmentDialog(product: Product): void {
    const dialogRef = this.dialog.open(StockAdjustmentDialog, {
      data: {
        productName: product.name,
        currentQuantity: product.inventory_items?.reduce((acc, item) => acc + item.quantity, 0) ?? 0,
      },
    });

    dialogRef.afterClosed().subscribe(adjustment => {
      if (adjustment) {
        this.productService.adjustStock(product.id, adjustment).subscribe();
      }
    });
  }

  onSearchQuery(query: string): void {
    if (query) {
      this.productService.searchProducts(query).subscribe();
    } else {
      this.productService.getProducts().subscribe();
    }
  }

  clearSearch(): void {
    this.productService.getProducts().subscribe();
  }

  getImageUrl(imagePath: string): string {
    // Backend serves images from the 'uploads/product_images' directory.
    return `/uploads/product_images/${imagePath}`;
  }

  getPrimaryImage(product: Product): string {
    // Return primary image if available
    if (product.primary_image) {
      return product.primary_image.image_path;
    }
    // Otherwise return the first image if available
    if (product.images && product.images.length > 0) {
      return product.images[0].image_path;
    }
    // Return placeholder if no images exist
    return 'placeholder.jpg';
  }

  onImageError(event: any): void {
    // Set a placeholder image if the image fails to load
    event.target.src = '/uploads/product_images/placeholder.jpg';
  }
}
