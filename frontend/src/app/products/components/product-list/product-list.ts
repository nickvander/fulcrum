import { Component, OnInit, OnDestroy, Output, EventEmitter, ViewChild } from '@angular/core';
import { ProductService } from '../../services/product';
import { Product } from '../../models/product.model';
import { PaginatedProducts } from '../../models/paginated-products.model';
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
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { InfiniteScrollDirective } from '../../directives/infinite-scroll.directive';

import { StockAdjustmentDialog } from '../stock-adjustment-dialog/stock-adjustment-dialog';
import { StockHistoryDialog } from '../stock-history-dialog/stock-history-dialog';
import { BatchActionToolbarComponent } from '../batch-action-toolbar/batch-action-toolbar';
import { ProductForm } from '../product-form/product-form';
import { PaginationComponent } from '../pagination/pagination';
import { ProductFiltersComponent } from '../product-filters/product-filters';
import { BatchOperationsService } from '../../services/batch-operations.service';
import { NotificationService } from '../../../core/services/notification.service';
import { ProductComparisonService } from '../../services/product-comparison.service';
import { ProductComparisonComponent } from '../product-comparison/product-comparison';

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
    MatProgressSpinnerModule,
    MatTooltipModule,
    InfiniteScrollDirective,
    BatchActionToolbarComponent,
    ProductForm,
    PaginationComponent,
    ProductFiltersComponent
  ],
})
export class ProductList implements OnInit, OnDestroy {
  @ViewChild('sidenav') sidenav!: MatSidenav;
  @ViewChild('filterSidenav') filterSidenav!: MatSidenav;
  
  products: Product[] = [];
  paginatedProducts: PaginatedProducts | null = null;
  selectedProducts = new Set<number>(); // Store IDs of selected products
  selectedProductForEdit: Product | null = null;
  isEditing = false;
  currentPage: number = 1;
  pageSize: number = 10;
  isLoading: boolean = false;
  activeFilters: any = {};
  showFilters: boolean = false; // Show/hide filter sidebar
  useInfiniteScroll: boolean = false; // Toggle between pagination and infinite scroll
  allProducts: Product[] = []; // For infinite scroll
  hasMoreProducts: boolean = true; // For infinite scroll
  private destroy$ = new Subject<void>();

  constructor(
    private productService: ProductService,
    private batchOperationsService: BatchOperationsService,
    private notificationService: NotificationService,
    private comparisonService: ProductComparisonService,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.loadProducts();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  isProductInComparison(product: Product): boolean {
    return this.comparisonService.isInComparison(product.id);
  }

  toggleProductComparison(product: Product): void {
    this.comparisonService.toggleProductInComparison(product);
  }

  openComparisonView(): void {
    // This would typically open the comparison in a dialog or separate view
    // For now, we'll just log the products that are being compared
    console.log('Opening comparison view for products:', this.comparisonService.getProducts());
  }

  loadProducts(page: number = 1, size: number = this.pageSize): void {
    this.isLoading = true;
    this.currentPage = page;
    this.pageSize = size;
    
    // Reset products if it's the first page for infinite scroll
    if (this.useInfiniteScroll && page === 1) {
      this.allProducts = [];
    }
    
    // Determine if we should use search or filtered endpoint
    const searchActive = Object.keys(this.activeFilters).some(key => 
      this.activeFilters[key] !== null && this.activeFilters[key] !== undefined && this.activeFilters[key] !== ''
    );
    
    if (this.useInfiniteScroll) {
      // For infinite scroll, we'll handle differently
      if (searchActive) {
        this.productService.searchProductsAdvanced(this.activeFilters, page, size).subscribe({
          next: (result) => {
            if (page === 1) {
              this.allProducts = result.data;
              this.products = result.data;
            } else {
              this.allProducts = [...this.allProducts, ...result.data];
              this.products = this.allProducts;
            }
            this.paginatedProducts = result;
            this.hasMoreProducts = result.currentPage < result.totalPages;
            this.isLoading = false;
          },
          error: (error) => {
            console.error('Error loading products with filters:', error);
            this.isLoading = false;
          }
        });
      } else {
        this.productService.getProducts(page, size, this.activeFilters).subscribe({
          next: (result) => {
            if (page === 1) {
              this.allProducts = result.data;
              this.products = result.data;
            } else {
              this.allProducts = [...this.allProducts, ...result.data];
              this.products = this.allProducts;
            }
            this.paginatedProducts = result;
            this.hasMoreProducts = result.currentPage < result.totalPages;
            this.isLoading = false;
          },
          error: (error) => {
            console.error('Error loading products:', error);
            this.isLoading = false;
          }
        });
      }
    } else {
      // For regular pagination
      if (searchActive) {
        // Use the advanced search endpoint with filters
        this.productService.searchProductsAdvanced(this.activeFilters, page, size).subscribe({
          next: (result) => {
            this.paginatedProducts = result;
            this.products = result.data;
            this.isLoading = false;
          },
          error: (error) => {
            console.error('Error loading products with filters:', error);
            this.isLoading = false;
          }
        });
      } else {
        // Use the regular getProducts endpoint with pagination and filters
        this.productService.getProducts(page, size, this.activeFilters).subscribe({
          next: (result) => {
            this.paginatedProducts = result;
            this.products = result.data;
            this.isLoading = false;
          },
          error: (error) => {
            console.error('Error loading products:', error);
            this.isLoading = false;
          }
        });
      }
    }
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
      // Update active filters to include search query
      this.activeFilters.search_term = query;
      this.loadProducts(1, this.pageSize);
    } else {
      // Remove search term from filters if query is empty
      delete this.activeFilters.search_term;
      this.loadProducts(1, this.pageSize);
    }
  }

  clearSearch(): void {
    delete this.activeFilters.search_term;
    this.loadProducts(1, this.pageSize);
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
    this.loadProducts(this.currentPage, this.pageSize);
    this.closeEditPanel();
  }
  
  onPageChange(page: number): void {
    if (this.paginatedProducts) {
      if (page >= 1 && page <= this.paginatedProducts.totalPages && page !== this.currentPage) {
        this.loadProducts(page, this.pageSize);
      }
    }
  }

  onPageSizeChange(size: number): void {
    this.loadProducts(1, size); // Reset to first page when page size changes
  }
  
  onFiltersChanged(filters: any): void {
    this.activeFilters = filters;
    this.loadProducts(1, this.pageSize); // Reset to first page when filters change
  }
  
  onFiltersCleared(): void {
    this.activeFilters = {};
  }
  
  toggleFilters(): void {
    this.showFilters = !this.showFilters;
  }
  
  toggleInfiniteScroll(): void {
    this.useInfiniteScroll = !this.useInfiniteScroll;
    
    if (this.useInfiniteScroll) {
      // Initialize for infinite scroll
      this.loadProducts(1, this.pageSize);
    } else {
      // Reset to regular pagination
      this.loadProducts(1, this.pageSize);
    }
  }
  
  onBatchPriceUpdate(event: {productIds: number[], price: number}): void {
    // Get the selected product IDs if not provided in the event
    const productIds = event.productIds.length === 0 ? Array.from(this.selectedProducts) : event.productIds;
    
    // In a real implementation, you would open a dialog to get the price adjustment
    // For now, let's just use a default value as an example
    const priceAdjustment = 10; // Example value - in reality you'd get this from a dialog
    const adjustmentType: 'set' | 'increase' = 'set'; // Example type
    
    this.batchOperationsService.batchUpdatePrices(productIds, priceAdjustment, adjustmentType).subscribe({
      next: () => {
        this.notificationService.showSuccess(`${productIds.length} products updated successfully!`);
        this.loadProducts(this.currentPage, this.pageSize); // Refresh the product list
        this.deselectAll(); // Clear selection after operation
      },
      error: (error) => {
        console.error('Error updating product prices:', error);
        this.notificationService.showError('Error updating product prices');
      }
    });
  }
  
  onBatchCategoryUpdate(event: {productIds: number[], category: string}): void {
    // Get the selected product IDs if not provided in the event
    const productIds = event.productIds.length === 0 ? Array.from(this.selectedProducts) : event.productIds;
    
    // In a real implementation, you would open a dialog to select the category
    // For now, let's just use a default value as an example
    const category = 'Electronics'; // Example value - in reality you'd get this from a dialog
    
    this.batchOperationsService.batchUpdateCategories(productIds, category).subscribe({
      next: () => {
        this.notificationService.showSuccess(`${productIds.length} products updated successfully!`);
        this.loadProducts(this.currentPage, this.pageSize); // Refresh the product list
        this.deselectAll(); // Clear selection after operation
      },
      error: (error) => {
        console.error('Error updating product categories:', error);
        this.notificationService.showError('Error updating product categories');
      }
    });
  }
  
  onBatchCustomFieldUpdate(event: {productIds: number[], updates: {[key: string]: any}}): void {
    // Get the selected product IDs if not provided in the event
    const productIds = event.productIds.length === 0 ? Array.from(this.selectedProducts) : event.productIds;
    
    // In a real implementation, you would open a dialog to specify custom field updates
    // For now, let's just use a default value as an example
    const updates = { warranty_period: '12 months' }; // Example value - in reality you'd get this from a dialog
    
    this.batchOperationsService.batchUpdateCustomFields(productIds, updates).subscribe({
      next: () => {
        this.notificationService.showSuccess(`${productIds.length} products updated successfully!`);
        this.loadProducts(this.currentPage, this.pageSize); // Refresh the product list
        this.deselectAll(); // Clear selection after operation
      },
      error: (error) => {
        console.error('Error updating custom fields:', error);
        this.notificationService.showError('Error updating custom fields');
      }
    });
  }
  
  applyQuickFilter(filterType: string, value: any): void {
    // Clear all other filters except the current one
    this.activeFilters = {};
    
    switch (filterType) {
      case 'in_stock':
        this.activeFilters.min_stock = 1;
        break;
      case 'out_of_stock':
        this.activeFilters.max_stock = 0;
        break;
      case 'low_stock':
        this.activeFilters.max_stock = 10; // Assuming low stock is under 10
        break;
      case 'on_sale':
        // This would be for products with special pricing
        // For now, we can implement this if we add a 'on_sale' property to products
        break;
      case 'expensive':
        this.activeFilters.min_price = 500; // Products over $500
        break;
      case 'cheap':
        this.activeFilters.max_price = 50; // Products under $50
        break;
      default:
        // For specific categories or brands
        this.activeFilters[filterType] = value;
        break;
    }
    
    this.loadProducts(1, this.pageSize);
  }
  
  onWindowScroll(): void {
    if (this.useInfiniteScroll && this.hasMoreProducts && !this.isLoading) {
      // Load next page
      const nextPage = this.paginatedProducts ? this.paginatedProducts.currentPage + 1 : 2;
      if (nextPage <= (this.paginatedProducts?.totalPages || 1)) {
        this.loadMoreProducts(nextPage, this.pageSize);
      }
    }
  }
  
  private loadMoreProducts(page: number, size: number): void {
    this.isLoading = true;
    
    // For infinite scroll, we'll need to get more products and append them
    const searchActive = Object.keys(this.activeFilters).some(key => 
      this.activeFilters[key] !== null && this.activeFilters[key] !== undefined && this.activeFilters[key] !== ''
    );
    
    if (searchActive) {
      this.productService.searchProductsAdvanced(this.activeFilters, page, size).subscribe({
        next: (result) => {
          // Append new products to existing products
          this.allProducts = [...this.allProducts, ...result.data];
          this.products = this.allProducts; // Update the displayed products
          this.paginatedProducts = result;
          this.hasMoreProducts = result.currentPage < result.totalPages;
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Error loading more products:', error);
          this.isLoading = false;
        }
      });
    } else {
      this.productService.getProducts(page, size, this.activeFilters).subscribe({
        next: (result) => {
          // Append new products to existing products
          this.allProducts = [...this.allProducts, ...result.data];
          this.products = this.allProducts; // Update the displayed products
          this.paginatedProducts = result;
          this.hasMoreProducts = result.currentPage < result.totalPages;
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Error loading more products:', error);
          this.isLoading = false;
        }
      });
    }
  }
}
