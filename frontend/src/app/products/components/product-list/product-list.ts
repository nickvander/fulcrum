import { Component, OnInit, OnDestroy, Output, EventEmitter, ViewChild } from '@angular/core';
import { ProductService } from '../../services/product';
import { Product } from '../../models/product.model';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSidenavModule } from '@angular/material/sidenav';
import { SharedModule } from '../../../shared/shared-module';
import { RouterModule } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { ConfirmationDialog } from '../../../shared/components/confirmation-dialog/confirmation-dialog';
import { Subject, takeUntil } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatSidenav } from '@angular/material/sidenav';

import { StockAdjustmentDialog } from '../stock-adjustment-dialog/stock-adjustment-dialog';
import { StockHistoryDialog } from '../stock-history-dialog/stock-history-dialog';
import { BatchActionToolbarComponent } from '../batch-action-toolbar/batch-action-toolbar';
import { ProductForm } from '../product-form/product-form';

@Component({
  selector: 'app-product-list',
  templateUrl: './product-list.html',
  styleUrls: ['./product-list.scss'],
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    SharedModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatCheckboxModule,
    MatSidenavModule,
    BatchActionToolbarComponent,
    ProductForm
  ],
})
export class ProductList implements OnInit, OnDestroy {
  @ViewChild('sidenav') sidenav!: MatSidenav;
  
  products: Product[] = [];
  selectedProducts = new Set<number>(); // Store IDs of selected products
  selectedProductForEdit: Product | null = null;
  isEditing = false;
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
    // Calculate current quantity: look for inventory item with 'default' location (main stock) 
    // or fall back to sum of all inventory items, or 0 if none exist
    let currentQuantity = 0;
    if (product.inventory_items && product.inventory_items.length > 0) {
      const mainInventory = product.inventory_items.find(item => item.location === 'default');
      if (mainInventory) {
        currentQuantity = mainInventory.quantity;
      } else {
        // Fallback: sum all inventory items if no 'default' location found
        currentQuantity = product.inventory_items.reduce((acc, item) => acc + item.quantity, 0);
      }
    }

    const dialogRef = this.dialog.open(StockAdjustmentDialog, {
      width: '400px', // Fixed width for consistency
      data: {
        productName: product.name,
        currentQuantity: currentQuantity,
      },
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result && result.adjustment) {
        this.productService.adjustStockWithReason(product.id, result.adjustment, result.reason).subscribe({
          next: () => {
            // The productService.adjustStock already calls getProducts() which should update the observable
            // but we'll make sure the UI refreshes by triggering change detection if needed
          },
          error: (error) => {
            console.error('Error adjusting stock:', error);
            this.productService.getProducts().subscribe(); // Ensure we refresh even on error
          }
        });
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

  onEditProduct(product: Product): void {
    // This method is no longer used since we directly call openEditPanel
  }

  toggleProductSelection(product: Product): void {
    if (this.selectedProducts.has(product.id)) {
      this.selectedProducts.delete(product.id);
    } else {
      this.selectedProducts.add(product.id);
    }
  }

  isSelected(product: Product): boolean {
    return this.selectedProducts.has(product.id);
  }

  getSelectedCount(): number {
    return this.selectedProducts.size;
  }

  selectAll(): void {
    this.products.forEach(product => {
      this.selectedProducts.add(product.id);
    });
  }

  deselectAll(): void {
    this.selectedProducts.clear();
  }

  deleteSelected(): void {
    if (this.selectedProducts.size === 0) return;

    const dialogRef = this.dialog.open(ConfirmationDialog, {
      data: {
        title: 'Delete Selected Products',
        message: `Are you sure you want to delete ${this.selectedProducts.size} product(s)? This action cannot be undone.`
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        // Convert selected product IDs to an array for processing
        const selectedIds = Array.from(this.selectedProducts);
        
        // Delete all selected products
        this.productService.deleteMultipleProducts(selectedIds).subscribe({
          next: () => {
            // Refresh the product list after deletion
            this.productService.getProducts().subscribe();
            // Clear the selection
            this.selectedProducts.clear();
          },
          error: (error) => {
            console.error('Error deleting selected products:', error);
          }
        });
      }
    });
  }

  onAddProduct(): void {
    // This method is no longer used since routing handles adding
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

  getCurrentStock(product: Product): number {
    // Calculate current quantity: look for inventory item with 'default' location (main stock) 
    // or fall back to sum of all inventory items, or 0 if none exist
    if (product.inventory_items && product.inventory_items.length > 0) {
      const mainInventory = product.inventory_items.find(item => item.location === 'default');
      if (mainInventory) {
        return mainInventory.quantity;
      } else {
        // Fallback: sum all inventory items if no 'default' location found
        return product.inventory_items.reduce((acc, item) => acc + item.quantity, 0);
      }
    }
    return 0;
  }

  showStockHistory(product: Product): void {
    const dialogRef = this.dialog.open(StockHistoryDialog, {
      width: '600px',
      data: {
        productName: product.name,
        currentStock: this.getCurrentStock(product),
        inventoryAdjustments: product.inventory_adjustments || []
      }
    });
  }

  onImageError(event: any): void {
    // Set a placeholder image if the image fails to load
    event.target.src = '/uploads/product_images/placeholder.jpg';
  }
  
  openEditPanel(product: Product): void {
    this.selectedProductForEdit = product;
    this.isEditing = true;
    setTimeout(() => {  // Use setTimeout to ensure sidenav is rendered
      this.sidenav?.open();
    }, 0);
  }
  

  
  closeEditPanel(): void {
    this.sidenav?.close();
    this.selectedProductForEdit = null;
  }
  
  onProductSaved(): void {
    // Refresh the product list after saving
    this.productService.getProducts().subscribe();
    this.closeEditPanel();
  }
}
