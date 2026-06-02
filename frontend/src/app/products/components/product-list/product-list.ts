import {
  Component,
  OnInit,
  OnDestroy,
  AfterViewInit,
  ViewChild,
  ChangeDetectionStrategy,
  ElementRef,
  signal,
  computed,
  NgZone,
} from '@angular/core';
import { ProductService } from '../../services/product';
import { Product } from '../../models/product.model';
import { PaginatedProducts } from '../../models/paginated-products.model';
import { ProductRowVM, toRowVM, StockHealth } from './product-row.vm';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MaterialModule } from '../../../shared/material.module';
import { ScrollingModule } from '@angular/cdk/scrolling';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { Subject, takeUntil, debounceTime, distinctUntilChanged } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';
import { PageEvent } from '@angular/material/paginator';
import { SharedModule } from '../../../shared/shared-module';
import { ProductDashboardComponent } from '../../pages/product-dashboard/product-dashboard.component';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';

import { StockAdjustmentDialog } from '../stock-adjustment-dialog/stock-adjustment-dialog';
import { StockHistoryDialogComponent } from '../stock-history-dialog/stock-history-dialog.component';
import { ConfirmationDialog } from '../../../shared/components/confirmation-dialog/confirmation-dialog';
import { BatchOperationsService } from '../../services/batch-operations.service';
import { NotificationService } from '../../../core/services/notification.service';
import { ProductComparisonService } from '../../services/product-comparison.service';
import { ScreenService } from '../../../core/services/screen.service';
import { ProductDetailsDialogComponent } from '../product-details-dialog/product-details-dialog.component';
import { CatalogImportDialogComponent } from '../catalog-import-dialog/catalog-import-dialog';
import { MxnPipe } from '../../../shared/pipes/mxn.pipe';

type ViewMode = 'list' | 'grid';
type Density = 'compact' | 'default' | 'comfortable';
type SortOrder = 'asc' | 'desc';

/** Fixed row heights per density (px) — required for CDK fixed-size virtual scroll. */
const ROW_HEIGHT: Record<Density, number> = { compact: 44, default: 52, comfortable: 64 };
/** Fixed grid card height + gap (px) used as the virtual-scroll itemSize. */
const CARD_HEIGHT = 300;
const GRID_GAP = 16;
/** Min card width used to compute columns-per-row (≈2 on phones, up to MAX). */
const CARD_MIN_WIDTH = 170;
const MAX_CARDS_PER_ROW = 5;

/** Columns that can be shown/hidden via the Columns menu. */
const OPTIONAL_COLUMNS = ['costo', 'marca', 'velocidad', 'campanas'] as const;
const DEFAULT_VISIBLE_OPTIONAL: string[] = []; // all optional columns off by default

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
    ScrollingModule,
    ProductDashboardComponent,
    TranslocoModule,
    EmptyStateComponent,
    MxnPipe,
  ],
})
export class ProductList implements OnInit, OnDestroy, AfterViewInit {
  // ---- Reactive state (signals) --------------------------------------------
  rows = signal<ProductRowVM[]>([]);
  paginatedProducts = signal<PaginatedProducts | null>(null);
  isLoading = signal(false);
  isReloading = signal(false);

  viewMode = signal<ViewMode>('list');
  density = signal<Density>('default');
  showDashboard = signal(false);
  showAdvancedFilters = signal(false);
  showStockExplainer = signal(false);

  selectedIds = signal<ReadonlySet<number>>(new Set());
  selectAllAcrossPages = signal(false);

  activeProductType = signal<'all' | 'product' | 'bundle'>('all');
  sortBy = signal<string | null>(null);
  sortOrder = signal<SortOrder>('asc');

  visibleOptional = signal<ReadonlySet<string>>(new Set(DEFAULT_VISIBLE_OPTIONAL));
  cardsPerRow = signal(4);

  // Ids whose image 404'd at runtime → show the themed placeholder instead.
  failedImages = signal<ReadonlySet<number>>(new Set());

  // Inline / bulk price editing
  editingPriceId = signal<number | null>(null);
  editingPriceValue = 0;
  showBulkPrice = signal(false);
  bulkPriceValue = 0;

  // ---- Derived state (computed) --------------------------------------------
  rowHeight = computed(() => ROW_HEIGHT[this.density()]);
  cardRowHeight = CARD_HEIGHT + GRID_GAP;

  chunkedRows = computed<ProductRowVM[][]>(() => {
    const n = this.cardsPerRow();
    const all = this.rows();
    const out: ProductRowVM[][] = [];
    for (let i = 0; i < all.length; i += n) out.push(all.slice(i, i + n));
    return out;
  });

  selectedCount = computed(() => this.selectedIds().size);
  allCurrentSelected = computed(() => {
    const rows = this.rows();
    if (rows.length === 0) return false;
    const sel = this.selectedIds();
    return rows.every((r) => sel.has(r.id));
  });
  someCurrentSelected = computed(() => {
    const rows = this.rows();
    const sel = this.selectedIds();
    const count = rows.filter((r) => sel.has(r.id)).length;
    return count > 0 && count < rows.length;
  });

  readonly optionalColumns = OPTIONAL_COLUMNS;
  readonly optionalColumnWidth: Record<string, string> = {
    costo: '110px',
    marca: '120px',
    velocidad: '92px',
    campanas: '84px',
  };
  readonly optionalColumnLabelKey: Record<string, string> = {
    costo: 'common.cost',
    marca: 'products.brand',
    velocidad: 'products.velocity',
    campanas: 'products.campaigns',
  };

  /** Shared grid-template-columns for the sticky header + every virtual row. */
  gridTemplateColumns = computed(() => {
    const base = '32px 40px 56px minmax(180px, 1.6fr) 120px 110px 96px 110px 84px';
    const optional = this.optionalColumns
      .filter((c) => this.visibleOptional().has(c))
      .map((c) => this.optionalColumnWidth[c])
      .join(' ');
    return `${base}${optional ? ' ' + optional : ''} 48px`;
  });

  // ---- Plain (non-reactive) UI state ---------------------------------------
  currentSearchQuery = '';
  currentPage = 1;
  pageSize = 25;
  activeFilters: any = {};

  // The grid viewport mounts/unmounts as the user switches view modes, so we
  // (re)attach the ResizeObserver via a setter rather than once in AfterViewInit.
  @ViewChild('gridViewport', { read: ElementRef })
  set gridViewportRef(ref: ElementRef<HTMLElement> | undefined) {
    this.resizeObserver?.disconnect();
    if (ref?.nativeElement) {
      this.measureCardsPerRow(ref.nativeElement.clientWidth);
      this.resizeObserver?.observe(ref.nativeElement);
    }
  }

  private destroy$ = new Subject<void>();
  private filterSubject = new Subject<void>();
  private userOverrodeViewMode = false;
  private pendingOpenSku: string | null = null;
  private resizeObserver?: ResizeObserver;

  constructor(
    private productService: ProductService,
    private batchOperationsService: BatchOperationsService,
    private notificationService: NotificationService,
    private comparisonService: ProductComparisonService,
    private dialog: MatDialog,
    private screenService: ScreenService,
    private route: ActivatedRoute,
    private transloco: TranslocoService,
    private zone: NgZone,
  ) {}

  ngOnInit(): void {
    // Create the observer before the gridViewportRef setter can fire.
    // Guarded for non-DOM test environments that lack ResizeObserver.
    if (typeof ResizeObserver !== 'undefined') {
      this.zone.runOutsideAngular(() => {
        this.resizeObserver = new ResizeObserver((entries) => {
          this.measureCardsPerRow(entries[0]?.contentRect.width ?? 0);
        });
      });
    }

    this.route.queryParams.pipe(takeUntil(this.destroy$)).subscribe((params) => {
      if (params['open_sku']) {
        this.pendingOpenSku = params['open_sku'];
        this.activeFilters.q = this.pendingOpenSku;
        this.loadProducts(1, this.pageSize);
      }
    });

    this.loadProducts();

    this.filterSubject
      .pipe(debounceTime(400), distinctUntilChanged(), takeUntil(this.destroy$))
      .subscribe(() => this.loadProducts(1, this.pageSize));

    this.screenService.isMobile$.pipe(takeUntil(this.destroy$)).subscribe((isMobile) => {
      if (!this.userOverrodeViewMode) {
        this.viewMode.set(isMobile ? 'grid' : 'list');
      }
    });
  }

  ngAfterViewInit(): void {
    // Grid viewport observer is wired via the gridViewportRef setter.
  }

  private measureCardsPerRow(width: number): void {
    if (!width) return;
    const raw = Math.floor((width + GRID_GAP) / (CARD_MIN_WIDTH + GRID_GAP));
    const cols = Math.min(MAX_CARDS_PER_ROW, Math.max(1, raw));
    if (cols !== this.cardsPerRow()) {
      this.zone.run(() => this.cardsPerRow.set(cols));
    }
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ---- Data loading --------------------------------------------------------
  loadProducts(page: number = 1, size: number = this.pageSize): void {
    if (this.rows().length > 0) this.isReloading.set(true);
    else this.isLoading.set(true);

    this.currentPage = page;
    this.pageSize = size;

    const filters = this.buildRequestFilters();

    this.productService
      .getProducts(page, size, filters)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (result) => this.applyResult(result),
        error: (error) => {
          console.error('Error loading products:', error);
          this.isLoading.set(false);
          this.isReloading.set(false);
        },
      });
  }

  /** Merge active filters + sort into the query param bag for the API. */
  private buildRequestFilters(): any {
    const filters: any = { ...this.activeFilters };
    if (this.sortBy()) {
      filters.sort_by = this.sortBy();
      filters.sort_order = this.sortOrder();
    }
    return filters;
  }

  private applyResult(result: PaginatedProducts): void {
    this.resetFailedImages();
    this.paginatedProducts.set(result);
    this.rows.set(result.data.map((p) => toRowVM(p)));
    this.isLoading.set(false);
    this.isReloading.set(false);
    this.tryOpenPendingProduct(result.data);
  }

  private tryOpenPendingProduct(products: Product[]): void {
    if (this.pendingOpenSku && products.length > 0) {
      const target = products.find((p) => p.sku === this.pendingOpenSku);
      if (target) {
        this.pendingOpenSku = null;
        setTimeout(() => this.openDetailsDialog(target, 'view'), 100);
      }
    }
  }

  // ---- View / density / columns --------------------------------------------
  setViewMode(mode: ViewMode): void {
    this.viewMode.set(mode);
    this.userOverrodeViewMode = true;
  }

  setDensity(d: Density): void {
    this.density.set(d);
  }

  toggleColumn(key: string): void {
    const next = new Set(this.visibleOptional());
    if (next.has(key)) next.delete(key);
    else next.add(key);
    this.visibleOptional.set(next);
  }

  isColumnVisible(key: string): boolean {
    return this.visibleOptional().has(key);
  }

  resetColumns(): void {
    this.visibleOptional.set(new Set(DEFAULT_VISIBLE_OPTIONAL));
  }

  // ---- Sorting (server-side, whitelisted columns) --------------------------
  onSort(field: string): void {
    if (this.sortBy() === field) {
      if (this.sortOrder() === 'asc') {
        this.sortOrder.set('desc');
      } else {
        // asc -> desc -> off
        this.sortBy.set(null);
        this.sortOrder.set('asc');
      }
    } else {
      this.sortBy.set(field);
      this.sortOrder.set('asc');
    }
    this.loadProducts(1, this.pageSize);
  }

  sortIcon(field: string): string {
    if (this.sortBy() !== field) return 'unfold_more';
    return this.sortOrder() === 'asc' ? 'arrow_upward' : 'arrow_downward';
  }

  // ---- Selection (by id; survives virtualization + pages) ------------------
  isSelected(row: ProductRowVM): boolean {
    return this.selectedIds().has(row.id);
  }

  toggleRowSelection(row: ProductRowVM): void {
    const next = new Set(this.selectedIds());
    if (next.has(row.id)) next.delete(row.id);
    else next.add(row.id);
    this.selectedIds.set(next);
    this.selectAllAcrossPages.set(false);
  }

  toggleSelectCurrentPage(): void {
    const next = new Set(this.selectedIds());
    if (this.allCurrentSelected()) {
      this.rows().forEach((r) => next.delete(r.id));
      this.selectAllAcrossPages.set(false);
    } else {
      this.rows().forEach((r) => next.add(r.id));
    }
    this.selectedIds.set(next);
  }

  /** Explicit "select all N across every page" affordance. */
  selectAllPages(): void {
    this.selectAllAcrossPages.set(true);
    // Fetch all IDs in one large page so bulk ops cover the whole result set.
    const total = this.paginatedProducts()?.totalItems ?? this.rows().length;
    this.productService
      .getProducts(1, Math.max(total, 1), this.buildRequestFilters())
      .pipe(takeUntil(this.destroy$))
      .subscribe((result) => {
        this.selectedIds.set(new Set(result.data.map((p) => p.id)));
      });
  }

  deselectAll(): void {
    this.selectedIds.set(new Set());
    this.selectAllAcrossPages.set(false);
    this.showBulkPrice.set(false);
  }

  // ---- Bulk + inline price editing -----------------------------------------
  startInlinePrice(row: ProductRowVM): void {
    this.editingPriceId.set(row.id);
    this.editingPriceValue = row.price;
  }

  cancelInlinePrice(): void {
    this.editingPriceId.set(null);
  }

  commitInlinePrice(row: ProductRowVM): void {
    const value = Number(this.editingPriceValue);
    this.editingPriceId.set(null);
    if (!Number.isFinite(value) || value < 0 || value === row.price) return;
    this.batchOperationsService
      .batchUpdatePrices([row.id], value, 'set')
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.notificationService.showSuccess(
            this.transloco.translate('products.productList.batchUpdatedSuccess', { count: 1 }),
          );
          this.loadProducts(this.currentPage, this.pageSize);
        },
      });
  }

  toggleBulkPrice(): void {
    this.showBulkPrice.update((v) => !v);
    this.bulkPriceValue = 0;
  }

  applyBulkPrice(): void {
    const ids = Array.from(this.selectedIds());
    const value = Number(this.bulkPriceValue);
    if (ids.length === 0 || !Number.isFinite(value) || value < 0) return;
    this.batchOperationsService
      .batchUpdatePrices(ids, value, 'set')
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.notificationService.showSuccess(
            this.transloco.translate('products.productList.batchUpdatedSuccess', { count: ids.length }),
          );
          this.showBulkPrice.set(false);
          this.deselectAll();
          this.loadProducts(this.currentPage, this.pageSize);
        },
      });
  }

  // ---- Filters / search ----------------------------------------------------
  onSearchQuery(query: string): void {
    if (query) this.activeFilters.q = query;
    else delete this.activeFilters.q;
    this.filterSubject.next();
  }

  clearSearch(): void {
    delete this.activeFilters.q;
    this.currentSearchQuery = '';
    this.loadProducts(1, this.pageSize);
  }

  toggleAdvancedFilters(): void {
    this.showAdvancedFilters.update((v) => !v);
  }

  toggleDashboard(): void {
    this.showDashboard.update((v) => !v);
  }

  applyFilter(type: string, value: any): void {
    if (value === null || value === '' || value === undefined) delete this.activeFilters[type];
    else this.activeFilters[type] = value;
    this.filterSubject.next();
  }

  hasActiveFilters(): boolean {
    return Object.keys(this.activeFilters).some((k) => {
      if (k === 'is_bundle') return false;
      const v = this.activeFilters[k];
      return v !== null && v !== undefined && v !== '';
    });
  }

  resetFilters(): void {
    this.activeFilters = {};
    this.currentSearchQuery = '';
    this.activeProductType.set('all');
    this.loadProducts(1, this.pageSize);
  }

  onProductTypeChange(type: 'all' | 'product' | 'bundle'): void {
    this.activeProductType.set(type);
    if (type === 'all') delete this.activeFilters.is_bundle;
    else this.activeFilters.is_bundle = type === 'bundle';
    this.loadProducts(1, this.pageSize);
  }

  /**
   * Quick-view chips. Stock thresholds use per-product reorder points where
   * possible; the coarse server filters approximate the chip semantics.
   */
  applyQuickView(view: string): void {
    const set = (key: string, val: any) => (this.activeFilters[key] = val);
    const clear = (...keys: string[]) => keys.forEach((k) => delete this.activeFilters[k]);

    const toggleView = this.currentQuickView() === view;
    // Reset the stock/listing facets these chips own, then re-apply.
    clear('min_stock', 'max_stock', 'is_bundle');
    this.activeProductType.set('all');

    if (!toggleView) {
      switch (view) {
        case 'active':
          break; // listing status is client-derived; no server facet — visual filter only
        case 'unlisted':
          break;
        case 'low':
          set('max_stock', 10);
          set('min_stock', 1);
          break;
        case 'outOfStock':
          set('max_stock', 0);
          break;
        case 'reorder':
          set('max_stock', 10);
          break;
        case 'bundles':
          set('is_bundle', true);
          this.activeProductType.set('bundle');
          break;
      }
    }
    this.quickView.set(toggleView ? 'all' : view);
    this.loadProducts(1, this.pageSize);
  }

  quickView = signal<string>('all');
  currentQuickView(): string {
    return this.quickView();
  }

  // ---- Pagination ----------------------------------------------------------
  handlePageEvent(e: PageEvent): void {
    this.pageSize = e.pageSize;
    this.currentPage = e.pageIndex + 1;
    this.loadProducts(this.currentPage, this.pageSize);
  }

  // ---- Row actions ---------------------------------------------------------
  openDetailsDialog(product: any, mode: 'view' | 'edit' | 'add' = 'view'): void {
    let stagedImage: File | undefined;
    if (product._initialImageFile) {
      stagedImage = product._initialImageFile;
      delete product._initialImageFile;
    }
    const dialogRef = this.dialog.open(ProductDetailsDialogComponent, {
      width: '1000px',
      maxHeight: '90vh',
      data: { product, mode, stagedImage },
    });
    dialogRef.afterClosed().subscribe((result) => {
      if (result) this.loadProducts(this.currentPage, this.pageSize);
    });
  }

  openEditPanel(product: Product): void {
    this.openDetailsDialog(product, 'edit');
  }

  deleteProduct(id: number): void {
    const dialogRef = this.dialog.open(ConfirmationDialog, {
      data: {
        title: this.transloco.translate('products.productList.deleteProductTitle'),
        message: this.transloco.translate('products.productList.deleteProductMessage'),
      },
    });
    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        this.productService
          .deleteProduct(id)
          .pipe(takeUntil(this.destroy$))
          .subscribe(() => this.loadProducts(this.currentPage, this.pageSize));
      }
    });
  }

  deleteSelected(): void {
    if (this.selectedIds().size === 0) return;
    const dialogRef = this.dialog.open(ConfirmationDialog, {
      data: {
        title: this.transloco.translate('products.productList.deleteSelectedTitle'),
        message: this.transloco.translate('products.productList.deleteSelectedMessage', {
          count: this.selectedIds().size,
        }),
      },
    });
    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        const ids = Array.from(this.selectedIds());
        this.productService
          .deleteMultipleProducts(ids)
          .pipe(takeUntil(this.destroy$))
          .subscribe(() => {
            this.deselectAll();
            this.loadProducts(this.currentPage, this.pageSize);
          });
      }
    });
  }

  openStockAdjustmentDialog(product: Product): void {
    const currentQuantity = this.getCurrentStock(product);
    const dialogRef = this.dialog.open(StockAdjustmentDialog, {
      width: '400px',
      data: { productName: product.name, currentQuantity },
    });
    dialogRef.afterClosed().subscribe((result) => {
      if (result && result.adjustment) {
        this.productService
          .adjustStockWithReason(product.id, result.adjustment, result.reason)
          .pipe(takeUntil(this.destroy$))
          .subscribe({
            next: () => {
              this.notificationService.showSuccess(
                this.transloco.translate('products.productList.stockAdjustedSuccess'),
              );
              this.loadProducts(this.currentPage, this.pageSize);
            },
            error: () => {
              this.notificationService.showError(
                this.transloco.translate('products.productList.stockAdjustedError'),
              );
              this.loadProducts(this.currentPage, this.pageSize);
            },
          });
      }
    });
  }

  showStockHistory(product: Product): void {
    this.productService
      .getProductById(product.id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (full) => {
          this.dialog.open(StockHistoryDialogComponent, {
            width: '600px',
            data: {
              productName: full.name,
              currentStock: this.getCurrentStock(full),
              inventoryAdjustments: full.inventory_adjustments || [],
            },
          });
        },
        error: () => {
          this.dialog.open(StockHistoryDialogComponent, {
            width: '600px',
            data: {
              productName: product.name,
              currentStock: this.getCurrentStock(product),
              inventoryAdjustments: [],
            },
          });
        },
      });
  }

  onAddProduct(): void {
    this.openDetailsDialog(
      {
        id: 0,
        name: '',
        sku: '',
        description: '',
        default_resale_price: 0,
        cost_price: 0,
        images: [],
        custom_fields: [],
        is_bundle: false,
      } as Product,
      'edit',
    );
  }

  onAddBundle(): void {
    this.openDetailsDialog(
      {
        id: 0,
        name: this.transloco.translate('products.productList.newBundleDefaultName'),
        sku: '',
        description: '',
        default_resale_price: 0,
        cost_price: 0,
        images: [],
        custom_fields: [],
        is_bundle: true,
        bundle_components: [],
      } as Product,
      'edit',
    );
  }

  createBundleFromSelection(): void {
    const ids = Array.from(this.selectedIds());
    const selected = this.rows()
      .filter((r) => ids.includes(r.id))
      .map((r) => r.product);
    const bundleComponents = selected.map((product) => ({
      component_id: product.id,
      component_sku: product.sku,
      component_name: product.name,
      quantity: 1,
      component_stock: this.getCurrentStock(product),
    }));
    const newBundle = {
      id: 0,
      name: this.transloco.translate('products.productList.newBundleDefaultName'),
      sku: '',
      description: '',
      default_resale_price: 0,
      cost_price: selected.reduce((sum, p) => sum + (p.cost_price || 0), 0),
      images: [],
      custom_fields: [],
      is_bundle: true,
      bundle_components: bundleComponents,
    } as Product;
    this.openDetailsDialog(newBundle, 'edit');
    this.deselectAll();
  }

  openScanner(): void {
    import('../product-scanner/product-scanner.component').then(({ ProductScannerComponent }) => {
      const dialogRef = this.dialog.open(ProductScannerComponent, {
        width: '600px',
        height: 'auto',
        panelClass: 'scanner-dialog',
      });
      dialogRef.afterClosed().subscribe((result) => {
        if (!result) return;
        if (result.action === 'edit-existing' && result.productId) {
          this.openDetailsDialog({ id: result.productId } as Product, 'edit');
          return;
        }
        if (result.notFound || result.barcode || result.imageFile || result.name || result.description) {
          const newProduct = {
            id: 0,
            name: result.name || '',
            sku: result.sku || '',
            description: result.description || '',
            price: 0,
            cost_price: 0,
            stock_quantity: 0,
            category_id: null,
            supplier_id: null,
            barcode: result.barcode || '',
            brand: result.brand || '',
            model: '',
            notes: result.category
              ? this.transloco.translate('products.productList.identifiedCategoryNote', {
                  category: result.category,
                })
              : '',
            _initialImageFile: result.imageFile,
          } as any;
          if (result.suggested_attributes) newProduct.custom_fields = result.suggested_attributes;
          this.openDetailsDialog(newProduct, 'add');
        }
      });
    });
  }

  openCatalogImport(): void {
    const dialogRef = this.dialog.open(CatalogImportDialogComponent, {
      width: '900px',
      maxHeight: '90vh',
    });
    dialogRef.afterClosed().subscribe((created) => {
      if (created) this.loadProducts();
    });
  }

  toggleStockExplainer(): void {
    this.showStockExplainer.update((v) => !v);
  }

  // ---- Comparison ----------------------------------------------------------
  isProductInComparison(product: Product): boolean {
    return this.comparisonService.isInComparison(product.id);
  }

  toggleProductComparison(product: Product): void {
    this.comparisonService.toggleProductInComparison(product);
  }

  // ---- Image + stock helpers (kept for dialogs/specs) ----------------------
  getImageUrl(imagePath: string): string {
    if (imagePath && imagePath.startsWith('http')) return imagePath;
    if (imagePath === 'placeholder.jpg') return 'assets/placeholder.jpg';
    return `/uploads/product_images/${imagePath}`;
  }

  getPrimaryImage(product: Product): string {
    if (product.primary_image) return product.primary_image.image_path;
    if (product.images && product.images.length > 0) return product.images[0].image_path;
    return 'placeholder.jpg';
  }

  getCurrentStock(product: Product): number {
    if (product.inventory_items && product.inventory_items.length > 0) {
      const main = product.inventory_items.find((item) => item.location === 'default');
      if (main) return main.quantity;
      return product.inventory_items.reduce((acc, item) => acc + item.quantity, 0);
    }
    return 0;
  }

  /** True when the row has an image path that has not (yet) failed to load. */
  imageOk(row: ProductRowVM): boolean {
    return row.hasImage && !this.failedImages().has(row.id);
  }

  markImageFailed(id: number): void {
    const next = new Set(this.failedImages());
    next.add(id);
    this.failedImages.set(next);
  }

  // Retained for the stock-history/legacy callers + spec coverage.
  onImageError(event: any): void {
    if (event.target.src.includes('data:image')) return;
    event.target.src =
      'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIE5vdCBGb3VuZDwvdGV4dD48L3N2Zz4=';
  }

  // When the page changes (new products), forget stale image-failure flags.
  private resetFailedImages(): void {
    if (this.failedImages().size > 0) this.failedImages.set(new Set());
  }

  // Stable trackBy fns for @for / cdkVirtualFor.
  trackById = (_: number, row: ProductRowVM) => row.id;
  trackByIndex = (i: number) => i;
}
