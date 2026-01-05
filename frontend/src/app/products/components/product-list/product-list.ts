import { Component, OnInit, OnDestroy, AfterViewInit, Output, EventEmitter, ViewChild, ChangeDetectionStrategy, ChangeDetectorRef, ElementRef, HostListener } from '@angular/core';
import { ProductService } from '../../services/product';
import { Product } from '../../models/product.model';
import { PaginatedProducts } from '../../models/paginated-products.model';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MaterialModule } from '../../../shared/material.module';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { Subject, takeUntil, debounceTime, distinctUntilChanged } from 'rxjs';
import { MatTableDataSource } from '@angular/material/table';
import { MatSort } from '@angular/material/sort';
import { MatDialog } from '@angular/material/dialog';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { SharedModule } from '../../../shared/shared-module';
import { ProductDashboardComponent } from '../../pages/product-dashboard/product-dashboard.component';
import { TranslocoModule } from '@ngneat/transloco';

import { StockAdjustmentDialog } from '../stock-adjustment-dialog/stock-adjustment-dialog';
import { StockHistoryDialogComponent } from '../stock-history-dialog/stock-history-dialog.component';
import { ConfirmationDialog } from '../../../shared/components/confirmation-dialog/confirmation-dialog';
import { BatchOperationsService } from '../../services/batch-operations.service';
import { NotificationService } from '../../../core/services/notification.service';
import { ProductComparisonService } from '../../services/product-comparison.service';
import { ScreenService } from '../../../core/services/screen.service';
import { MarketplaceStatusComponent } from '../../../shared/components/marketplace-status/marketplace-status.component';
import { ProductDetailsDialogComponent } from '../product-details-dialog/product-details-dialog.component';

@Component({
  selector: 'app-product-list',
  templateUrl: './product-list.html',
  styleUrls: ['./product-list.scss'],
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    SharedModule,
    MaterialModule,
    MarketplaceStatusComponent,
    ProductDashboardComponent,
    TranslocoModule,
    LoadingSpinnerComponent,
    EmptyStateComponent
  ],
})
export class ProductList implements OnInit, OnDestroy, AfterViewInit {
  // HostListener for window scroll - primary scroll detection
  @HostListener('window:scroll')
  onWindowScrollEvent(): void {
    this.handleWindowScroll();
  }

  // @ViewChild(MatSort) handled via setter below

  products: Product[] = [];
  paginatedProducts: PaginatedProducts | null = null;
  currentSearchQuery: string = '';

  showDashboard = false; // Drawer state
  showScrollFab = false; // Toggle visibility based on scroll

  // Table View Data Source
  dataSource: MatTableDataSource<Product> = new MatTableDataSource();
  displayedColumns: string[] = ['select', 'image', 'name', 'sku', 'cost_price', 'price', 'stock', 'marketplaces', 'actions'];

  // View/UI State
  viewMode: 'list' | 'grid' = 'list';
  activeProductType: 'all' | 'product' | 'bundle' = 'all';

  selectedProducts = new Set<number>(); // Store IDs of selected products
  currentPage: number = 1;
  pageSize: number = 25;
  isLoading: boolean = false;
  isReloading: boolean = false;
  activeFilters: any = {};

  // Restoring Infinite Scroll Support
  useInfiniteScroll: boolean = false;
  allProducts: Product[] = [];
  hasMoreProducts: boolean = true;

  @ViewChild('scrollContainer') scrollContainer!: ElementRef<HTMLElement>;

  private destroy$ = new Subject<void>();
  private filterSubject = new Subject<void>();
  private userOverrodeViewMode = false; // Track if user manually changed view
  private pendingOpenSku: string | null = null; // SKU to auto-open dialog for

  constructor(
    private productService: ProductService,
    private batchOperationsService: BatchOperationsService,
    private notificationService: NotificationService,
    private comparisonService: ProductComparisonService,
    private dialog: MatDialog,
    private cdr: ChangeDetectorRef,
    private screenService: ScreenService,
    private route: ActivatedRoute
  ) { }

  ngOnInit(): void {
    // Check for open_sku query param to auto-open product dialog
    this.route.queryParams.pipe(takeUntil(this.destroy$)).subscribe(params => {
      if (params['open_sku']) {
        this.pendingOpenSku = params['open_sku'];
        // Set search filter to SKU so the product appears in results
        this.activeFilters.q = this.pendingOpenSku;
        // Reload products with the SKU filter
        this.loadProducts(1, this.pageSize);
      }
    });

    // Initial load
    this.loadProducts();

    // Debounce filter updates
    this.filterSubject.pipe(
      debounceTime(400),
      takeUntil(this.destroy$)
    ).subscribe(() => {
      this.loadProducts(1, this.pageSize);
    });

    // Auto-switch to grid view on mobile (unless user overrode)
    this.screenService.isMobile$.pipe(
      takeUntil(this.destroy$)
    ).subscribe(isMobile => {
      if (!this.userOverrodeViewMode) {
        this.viewMode = isMobile ? 'grid' : 'list';
        this.cdr.markForCheck();
      }
    });
  }

  // sort property to store the MatSort instance
  sort: MatSort | null = null;

  @ViewChild(MatSort) set matSort(ms: MatSort) {
    this.sort = ms;
    if (this.sort) {
      this.dataSource.sort = this.sort;

      // Custom sorting accessor
      this.dataSource.sortingDataAccessor = (item: Product, property: string) => {
        switch (property) {
          case 'price':
            return item.default_resale_price || 0;
          case 'cost_price':
            return item.cost_price || 0;
          case 'stock':
            return this.getCurrentStock(item);
          case 'name':
            return item.name?.toLowerCase() || '';
          case 'sku':
            return item.sku?.toLowerCase() || '';
          default:
            return (item as any)[property];
        }
      };
    }
  }

  // ngAfterViewInit is no longer strictly needed for sort if we use the setter, 
  // but we keep the method signature to satisfy the interface if we keep the implements.
  ngAfterViewInit(): void {
    // Set up native scroll listener for infinite scroll
    if (this.scrollContainer?.nativeElement) {
      this.scrollContainer.nativeElement.addEventListener('scroll', this.handleScroll.bind(this));
    }

    // Add document-level scroll listener with capture phase for nested scroll containers
    document.addEventListener('scroll', (event) => {
      this.handleScrollFromDocument(event);
    }, true); // true = capture phase
  }

  private handleScrollFromDocument(event: Event): void {
    if (!this.useInfiniteScroll || !this.hasMoreProducts || this.isLoading) {
      return;
    }

    const target = event.target as HTMLElement;
    if (!target || target === document.documentElement) return;

    const { scrollTop, scrollHeight, clientHeight } = target;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

    if (distanceFromBottom <= 200) {
      this.checkAndLoadMore();
    }
  }

  private handleScroll(): void {
    const el = this.scrollContainer?.nativeElement;
    if (!el) return;

    if (!this.useInfiniteScroll || !this.hasMoreProducts || this.isLoading) {
      return;
    }

    const { scrollTop, scrollHeight, clientHeight } = el;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

    // Load more when within 200px of bottom
    if (distanceFromBottom <= 200) {
      this.checkAndLoadMore();
    }
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
    if (this.products.length > 0) {
      this.isReloading = true;
    } else {
      this.isLoading = true;
    }

    this.currentPage = page;
    this.pageSize = size;

    // Reset products if it's the first page for infinite scroll
    if (this.useInfiniteScroll && page === 1) {
      this.allProducts = [];
    }

    // Check if any filter OTHER than is_bundle is active OR if search query exists
    const searchActive = Object.keys(this.activeFilters).some(key => {
      if (key === 'is_bundle') return false;
      return this.activeFilters[key] !== null && this.activeFilters[key] !== undefined && this.activeFilters[key] !== '';
    });

    if (this.useInfiniteScroll) {
      // Infinite Scroll Logic
      if (searchActive) {
        this.productService.searchProductsAdvanced(this.activeFilters, page, size)
          .pipe(takeUntil(this.destroy$))
          .subscribe({
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
              this.isLoading = false; this.isReloading = false;
              this.updateDataSource();

              // Auto-open product dialog if pendingOpenSku match found
              if (this.pendingOpenSku) {
                const product = this.allProducts.find(p => p.sku === this.pendingOpenSku);
                if (product) {
                  this.openDetailsDialog(product, 'view');
                  this.pendingOpenSku = null; // Clear so we don't re-trigger
                }
              }

              this.cdr.markForCheck();
            },
            error: (error) => {
              console.error('Error loading products (Search + Infinite):', error);
              this.isLoading = false; this.isReloading = false;
              this.cdr.markForCheck();
            }
          });
      } else {
        this.productService.getProducts(page, size, this.activeFilters)
          .pipe(takeUntil(this.destroy$))
          .subscribe({
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
              this.isLoading = false; this.isReloading = false;
              this.updateDataSource();
              this.cdr.markForCheck();
            },
            error: (error) => {
              console.error('Error loading products (Infinite):', error);
              this.isLoading = false; this.isReloading = false;
              this.cdr.markForCheck();
            }
          });
      }
    } else {
      // Standard Pagination Logic
      if (searchActive) {
        this.productService.searchProductsAdvanced(this.activeFilters, page, size)
          .pipe(takeUntil(this.destroy$))
          .subscribe({
            next: (result) => {
              this.paginatedProducts = result;
              this.products = result.data;
              this.isLoading = false; this.isReloading = false;
              this.updateDataSource();
              this.cdr.markForCheck();
            },
            error: (error) => {
              console.error('Error loading products (Search + Pagination):', error);
              this.isLoading = false; this.isReloading = false;
              this.cdr.markForCheck();
            }
          });
      } else {
        this.productService.getProducts(page, size, this.activeFilters)
          .pipe(takeUntil(this.destroy$))
          .subscribe({
            next: (result) => {
              this.paginatedProducts = result;
              this.products = result.data;
              this.isLoading = false; this.isReloading = false;
              this.updateDataSource();
              this.cdr.markForCheck();
            },
            error: (error) => {
              console.error('Error loading products (Pagination):', error);
              this.isLoading = false; this.isReloading = false;
              this.cdr.markForCheck();
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
        this.productService.deleteProduct(id)
          .pipe(takeUntil(this.destroy$))
          .subscribe();
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
        this.productService.adjustStockWithReason(product.id, result.adjustment, result.reason)
          .pipe(takeUntil(this.destroy$))
          .subscribe({
            next: () => {
              this.notificationService.showSuccess('Stock adjusted successfully');
              this.loadProducts(this.currentPage, this.pageSize);
            },
            error: (error) => {
              console.error('Error adjusting stock:', error);
              this.notificationService.showError('Error adjusting stock');
              this.loadProducts(this.currentPage, this.pageSize); // Refresh anyway
            }
          });
      }
    });
  }

  onSearchQuery(query: string): void {
    if (query) {
      // Update active filters to include search query
      this.activeFilters.q = query;
      this.loadProducts(1, this.pageSize);
    } else {
      // Remove search term from filters if query is empty
      delete this.activeFilters.q;
      this.loadProducts(1, this.pageSize);
    }
  }

  clearSearch(): void {
    delete this.activeFilters.q;
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
        this.productService.deleteMultipleProducts(selectedIds)
          .pipe(takeUntil(this.destroy$))
          .subscribe({
            next: () => {
              // Refresh the product list after deletion
              this.productService.getProducts()
                .pipe(takeUntil(this.destroy$))
                .subscribe();
              // Clear the selection
              this.selectedProducts.clear();
            },
            error: (error) => {
              console.error('Error deleting selected products:', error);
            }
          });
      }
    }); // Closes dialogRef.afterClosed().subscribe
  } // Closes deleteSelected

  updateDataSource(): void {
    this.dataSource.data = this.products;
    if (this.sort) {
      this.dataSource.sort = this.sort;
    }

    // Auto-open product dialog if navigated with open_sku param
    this.tryOpenPendingProduct();
  }

  private tryOpenPendingProduct(): void {
    if (this.pendingOpenSku && this.products.length > 0) {
      const targetProduct = this.products.find(p => p.sku === this.pendingOpenSku);
      if (targetProduct) {
        // Clear pending SKU before opening dialog to prevent re-opening
        this.pendingOpenSku = null;
        // Use setTimeout to ensure DOM is updated first
        setTimeout(() => {
          this.openDetailsDialog(targetProduct, 'view');
        }, 100);
      }
    }
  }

  setViewMode(mode: 'grid' | 'list'): void {
    this.viewMode = mode;
    this.userOverrodeViewMode = true; // User manually changed, don't auto-switch
    // If switching to list, ensure data source is updated and sorted
    if (mode === 'list') {
      setTimeout(() => {
        this.updateDataSource();
      });
    }
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
    // If it's a bundle and has no physical items, calculate virtual stock
    if (product.is_bundle) {
      // Check if we have physical stock first (assembled kits)
      let physicalStock = 0;
      if (product.inventory_items && product.inventory_items.length > 0) {
        const mainInventory = product.inventory_items.find(item => item.location === 'default');
        if (mainInventory) physicalStock = mainInventory.quantity;
        else physicalStock = product.inventory_items.reduce((acc, item) => acc + item.quantity, 0);
      }

      // Calculate virtual stock based on components
      if (product.bundle_components && product.bundle_components.length > 0) {
        const maxBundles = product.bundle_components.map(bc => {
          const componentStock = bc.component_stock || 0;
          const required = bc.quantity || 1;
          return Math.floor(componentStock / required);
        });
        // Return min of all components + physical stock
        // (Assuming physical stock is essentially "pre-assembled" and we can assemble more from components)
        // For simple "virtual bundle" logic, stock IS the min of components.
        // If we support "Assembled" inventory, it would be Physical + Virtual.
        // Let's assume strict virtual for now unless physical exists.
        const virtualStock = Math.min(...maxBundles);

        // User Preference: Show usage "Reserved" (Physical) stock as the primary number.
        // We can show the potential "Assemblable" stock elsewhere or in a tooltip if needed.
        return physicalStock;
      }
      return physicalStock;
    }

    // Regular product logic
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
    const dialogRef = this.dialog.open(StockHistoryDialogComponent, {
      width: '600px',
      data: {
        productName: product.name,
        currentStock: this.getCurrentStock(product),
        inventoryAdjustments: product.inventory_adjustments || []
      }
    });
  }

  onImageError(event: any): void {
    // Prevent infinite loop by checking if we've already tried to load the placeholder
    if (event.target.src.includes('data:image')) {
      // Already showing a data URI, don't try again
      return;
    }

    // Set a data URI placeholder image if the image fails to load
    event.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIE5vdCBGb3VuZDwvdGV4dD48L3N2Zz4=';
  }

  openDetailsDialog(product: any, mode: 'view' | 'edit' | 'add' = 'view'): void {
    let stagedImage: File | undefined = undefined;

    // Extract temporary image file if present (from scanner)
    if (product._initialImageFile) {
      stagedImage = product._initialImageFile;
      delete product._initialImageFile;
    }

    const dialogRef = this.dialog.open(ProductDetailsDialogComponent, {
      width: '1000px',
      maxHeight: '90vh',
      data: { product, mode, stagedImage }
    });

    dialogRef.afterClosed().subscribe(result => {
      // If product was saved (result is true), we refresh the list
      if (result) {
        this.loadProducts(this.currentPage, this.pageSize);
      }
    });
  }

  onAddProduct(): void {
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
    this.openDetailsDialog(newProduct, 'edit');
  }

  onAddBundle(): void {
    const newBundle = {
      id: 0,
      name: 'New Bundle',
      sku: '',
      description: '',
      default_resale_price: 0,
      cost_price: 0,
      images: [],
      custom_fields: [],
      is_bundle: true,
      bundle_components: []
    } as Product;
    this.openDetailsDialog(newBundle, 'edit');
  }

  createBundleFromSelection(): void {
    // Get selected products
    const selectedProductIds = Array.from(this.selectedProducts);
    const selectedProductsList = this.products.filter(p => selectedProductIds.includes(p.id));

    // Create bundle components from selected products
    const bundleComponents = selectedProductsList.map(product => ({
      component_id: product.id,
      component_sku: product.sku,
      component_name: product.name,
      quantity: 1,
      component_stock: this.getCurrentStock(product)
    }));

    // Create new bundle pre-filled with components
    const newBundle = {
      id: 0,
      name: 'New Bundle',
      sku: '',
      description: '',
      default_resale_price: 0,
      cost_price: selectedProductsList.reduce((sum, p) => sum + (p.cost_price || 0), 0),
      images: [],
      custom_fields: [],
      is_bundle: true,
      bundle_components: bundleComponents
    } as Product;

    // Open dialog and clear selection
    this.openDetailsDialog(newBundle, 'edit');
    this.selectedProducts.clear();
    this.cdr.markForCheck();
  }

  openEditPanel(product: Product): void {
    this.openDetailsDialog(product, 'edit');
  }

  onProductSaved(): void {
    // Refresh the current page to ensure all changes are reflected
    this.loadProducts(this.currentPage, this.pageSize);
  }

  // Standard MatPaginator Event Handler
  handlePageEvent(e: PageEvent): void {
    this.pageSize = e.pageSize;
    this.currentPage = e.pageIndex + 1; // Paginator is 0-indexed, API is 1-indexed
    this.loadProducts(this.currentPage, this.pageSize);
  }

  // Legacy/Custom pagination glue (can be removed if app-pagination is removed)
  onPageChange(page: number): void {
    if (this.paginatedProducts) {
      if (page >= 1 && page <= this.paginatedProducts.totalPages && page !== this.currentPage) {
        this.loadProducts(page, this.pageSize);
      }
    }
  }

  onPageSizeChange(size: number): void {
    this.loadProducts(1, size);
  }



  toggleInfiniteScroll(): void {
    // Flip the value since we're using (click)
    this.useInfiniteScroll = !this.useInfiniteScroll;

    if (this.useInfiniteScroll) {
      // Initialize for infinite scroll - reset to first page
      this.allProducts = [];
      this.hasMoreProducts = true;
      this.loadProducts(1, this.pageSize);
    } else {
      // Reset to regular pagination
      this.loadProducts(1, this.pageSize);
    }
    this.cdr.markForCheck();
  }

  toggleDashboard(): void {
    this.showDashboard = !this.showDashboard;
  }

  onWindowScroll(): void {
    this.checkAndLoadMore();
  }

  private handleWindowScroll(): void {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0;
    const shouldShow = scrollTop > 300;

    if (this.showScrollFab !== shouldShow) {
      this.showScrollFab = shouldShow;
      this.cdr.markForCheck();
    }

    if (!this.useInfiniteScroll || !this.hasMoreProducts || this.isLoading) {
      console.log('[InfiniteScroll] Window scroll blocked:', {
        useInfiniteScroll: this.useInfiniteScroll,
        hasMoreProducts: this.hasMoreProducts,
        isLoading: this.isLoading
      });
      return;
    }

    const pos = window.innerHeight + window.scrollY;
    const max = document.documentElement.scrollHeight;
    const distanceFromBottom = max - pos;

    // Load more when within 200px of bottom
    if (distanceFromBottom <= 200) {
      this.checkAndLoadMore();
    }
  }

  onContainerScroll(event: Event): void {
    const container = event.target as HTMLElement;
    const { scrollTop, scrollHeight, clientHeight } = container;

    const shouldShow = scrollTop > 300;
    if (this.showScrollFab !== shouldShow) {
      this.showScrollFab = shouldShow;
      this.cdr.markForCheck();
    }

    if (!this.useInfiniteScroll || !this.hasMoreProducts || this.isLoading) {
      return;
    }

    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

    // Load more when within 200px of bottom
    if (distanceFromBottom <= 200) {
      this.checkAndLoadMore();
    }
  }

  private checkAndLoadMore(): void {
    if (!this.useInfiniteScroll || !this.hasMoreProducts || this.isLoading) {
      return;
    }
    // Load next page
    const nextPage = this.paginatedProducts ? this.paginatedProducts.currentPage + 1 : 2;
    if (nextPage <= (this.paginatedProducts?.totalPages || 1)) {
      this.loadMoreProducts(nextPage, this.pageSize);
    }
  }

  private loadMoreProducts(page: number, size: number): void {
    this.isLoading = true;
    this.cdr.markForCheck();

    // For infinite scroll, we'll need to get more products and append them
    const searchActive = Object.keys(this.activeFilters).some(key =>
      this.activeFilters[key] !== null && this.activeFilters[key] !== undefined && this.activeFilters[key] !== ''
    );

    if (searchActive) {
      this.productService.searchProductsAdvanced(this.activeFilters, page, size)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (result) => {
            // Append new products to existing products
            this.allProducts = [...this.allProducts, ...result.data];
            this.products = this.allProducts; // Update the displayed products
            this.paginatedProducts = result;
            this.hasMoreProducts = result.currentPage < result.totalPages;
            this.isLoading = false; this.isReloading = false;
            this.updateDataSource();
            this.cdr.markForCheck();
          },
          error: (error) => {
            console.error('Error loading more products:', error);
            this.isLoading = false; this.isReloading = false;
            this.cdr.markForCheck();
          }
        });
    } else {
      this.productService.getProducts(page, size, this.activeFilters)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (result) => {
            this.allProducts = [...this.allProducts, ...result.data];
            this.products = this.allProducts;
            this.paginatedProducts = result;
            this.hasMoreProducts = result.currentPage < result.totalPages;
            this.isLoading = false; this.isReloading = false;
            this.updateDataSource();
            this.cdr.markForCheck();
          },
          error: (error) => {
            console.error('Error loading more products:', error);
            this.isLoading = false; this.isReloading = false;
            this.cdr.markForCheck();
          }
        });
    }
  }

  onBatchPriceUpdate(event: { productIds: number[], price: number }): void {
    const productIds = event.productIds.length === 0 ? Array.from(this.selectedProducts) : event.productIds;
    const priceAdjustment = 10;
    const adjustmentType: 'set' | 'increase' = 'set';

    this.batchOperationsService.batchUpdatePrices(productIds, priceAdjustment, adjustmentType)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.notificationService.showSuccess(`${productIds.length} products updated successfully!`);
          this.loadProducts(this.currentPage, this.pageSize);
          this.deselectAll();
        },
        error: (error) => {
          this.notificationService.showError('Error updating product prices');
        }
      });
  }

  onBatchCategoryUpdate(event: { productIds: number[], category: string }): void {
    const productIds = event.productIds.length === 0 ? Array.from(this.selectedProducts) : event.productIds;
    const category = 'Electronics';

    this.batchOperationsService.batchUpdateCategories(productIds, category)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.notificationService.showSuccess(`${productIds.length} products updated successfully!`);
          this.loadProducts(this.currentPage, this.pageSize);
          this.deselectAll();
        },
        error: (error) => {
          this.notificationService.showError('Error updating product categories');
        }
      });
  }

  onBatchCustomFieldUpdate(event: { productIds: number[], updates: { [key: string]: any } }): void {
    const productIds = event.productIds.length === 0 ? Array.from(this.selectedProducts) : event.productIds;
    const updates = { warranty_period: '12 months' };

    this.batchOperationsService.batchUpdateCustomFields(productIds, updates)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.notificationService.showSuccess(`${productIds.length} products updated successfully!`);
          this.loadProducts(this.currentPage, this.pageSize);
          this.deselectAll();
        },
        error: (error) => {
          this.notificationService.showError('Error updating custom fields');
        }
      });
  }

  onProductTypeChange(type: 'all' | 'product' | 'bundle'): void {
    this.activeProductType = type;

    if (type === 'all') {
      delete this.activeFilters.is_bundle;
    } else if (type === 'product') {
      this.activeFilters.is_bundle = false;
    } else if (type === 'bundle') {
      this.activeFilters.is_bundle = true;
    }

    this.loadProducts(1, this.pageSize);
  }

  getEffectiveCost(product: Product): number {
    if (product.is_bundle && (!product.cost_price || product.cost_price === 0)) {
      if (product.bundle_components && product.bundle_components.length > 0) {
        return product.bundle_components.reduce((sum, bc) => {
          const cost = bc.component_cost || 0;
          return sum + (cost * bc.quantity);
        }, 0);
      }
    }
    return product.cost_price || 0;
  }

  getBundleAverageCost(product: Product): number {
    if (product.is_bundle && product.bundle_components && product.bundle_components.length > 0) {
      return product.bundle_components.reduce((sum, bc) => {
        const cost = bc.component_cost || 0;
        return sum + (cost * bc.quantity);
      }, 0);
    }
    return product.average_cost || 0;
  }

  getAllocatedBundleNames(product: Product): string {
    if (!product.part_of_bundles || product.part_of_bundles.length === 0) return '';
    const names = Array.from(new Set(product.part_of_bundles.map(b => b.bundle_name).filter(n => n)));
    return names.join(', ');
  }

  showAdvancedFilters = false;

  toggleAdvancedFilters(): void {
    this.showAdvancedFilters = !this.showAdvancedFilters;
  }

  applyFilter(type: string, value: any): void {
    if (value === null || value === '' || value === undefined) {
      delete this.activeFilters[type];
    } else {
      this.activeFilters[type] = value;
    }
    this.filterSubject.next();
  }

  resetFilters(): void {
    this.activeFilters = {};
    this.currentSearchQuery = '';
    this.activeProductType = 'all';
    this.loadProducts(1, this.pageSize);
  }

  applyQuickFilter(filterType: string, value: any): void {
    const toggle = (key: string, val: any) => {
      if (this.activeFilters[key] === val) {
        delete this.activeFilters[key];
      } else {
        this.activeFilters[key] = val;
      }
    };

    switch (filterType) {
      case 'in_stock':
        delete this.activeFilters.max_stock;
        toggle('min_stock', 1);
        break;
      case 'out_of_stock':
        delete this.activeFilters.min_stock;
        toggle('max_stock', 0);
        break;
      case 'low_stock':
        delete this.activeFilters.min_stock;
        toggle('max_stock', 10);
        break;
      case 'expensive':
        delete this.activeFilters.max_price;
        toggle('min_price', 500);
        break;
      case 'cheap':
        delete this.activeFilters.min_price;
        toggle('max_price', 50);
        break;
      default:
        this.activeFilters[filterType] = value;
        break;
    }

    this.loadProducts(1, this.pageSize);
  }

  openScanner(): void {
    import('../product-scanner/product-scanner.component').then(({ ProductScannerComponent }) => {
      const dialogRef = this.dialog.open(ProductScannerComponent, {
        width: '600px',
        height: 'auto',
        panelClass: 'scanner-dialog'
      });

      dialogRef.afterClosed().subscribe(result => {
        if (!result) return;

        console.log('[ProductList] Scanner result:', result);

        // Case 1: Edit Existing (Explicit Action from Product Found UI)
        if (result.action === 'edit-existing' && result.productId) {
          this.openDetailsDialog({ id: result.productId } as Product, 'edit');
          return;
        }

        // Case 2: Create New (from AI result or Manual Scan)
        // Ensure we check for valid data before creating
        if (result.notFound || result.barcode || result.imageFile || result.name || result.description) {
          const newProduct = {
            id: 0,
            name: '',
            sku: '',
            description: '',
            price: 0,
            cost_price: 0,
            stock_quantity: 0,
            category_id: null,
            supplier_id: null,
            barcode: result.barcode || '',
            brand: '',
            model: '',
            notes: '',
            // Pass the image file if available. 
            // Note: The OpenDetailsDialog handles 'add' mode, we need to ensure it processes this field.
            // We'll attach it as a temporary property.
            _initialImageFile: result.imageFile
          } as any;

          // Pre-fill AI data if available (spread directly on result)
          if (result.name || result.description) {
            newProduct.name = result.name || '';
            newProduct.brand = result.brand || '';
            newProduct.description = result.description || '';
            if (result.sku) newProduct.sku = result.sku;

            // Map Category name to notes for now since we need ID
            if (result.category) {
              newProduct.notes = `Identified Category: ${result.category}`;
            }

            // Add suggested attributes to custom fields or notes
            if (result.suggested_attributes) {
              newProduct.custom_fields = result.suggested_attributes;
            }
          }

          this.openDetailsDialog(newProduct, 'add');
        }
      });
    });
  }
}

