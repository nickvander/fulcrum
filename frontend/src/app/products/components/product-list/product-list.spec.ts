import type { MockedObject } from "vitest";
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { ProductList } from './product-list';
import { ProductForm } from '../product-form/product-form';
import { BatchActionToolbarComponent } from '../batch-action-toolbar/batch-action-toolbar';
import { Directive } from '@angular/core';
import { PaginationComponent } from '../pagination/pagination';
import { ProductFiltersComponent } from '../product-filters/product-filters';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { ProductService } from '../../services/product';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { of, BehaviorSubject } from 'rxjs';
import { Product } from '../../models/product.model';
import { PaginatedProducts } from '../../models/paginated-products.model';
import { Component, NO_ERRORS_SCHEMA } from '@angular/core';
import { SharedModule } from '../../../shared/shared-module';
import { BatchOperationsService } from '../../services/batch-operations.service';
import { NotificationService } from '../../../core/services/notification.service';
import { ProductComparisonService } from '../../services/product-comparison.service';
import { MarketplaceStatusComponent } from '../../../shared/components/marketplace-status/marketplace-status.component';
import { AiSearchBar } from '../../../shared/components/ai-search-bar/ai-search-bar';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';

// Create a stub for the AiSearchBar component
@Component({
    selector: 'app-ai-search-bar',
    template: '',
    standalone: true,
})
class AiSearchBarStubComponent {
}

@Component({
    selector: 'app-product-form',
    template: '',
    standalone: true
})
class ProductFormStubComponent {
}

@Component({
    selector: 'app-batch-action-toolbar',
    template: '',
    standalone: true
})
class BatchActionToolbarStubComponent {
}

@Component({
    selector: 'app-pagination',
    template: '',
    standalone: true
})
class PaginationStubComponent {
}

@Component({
    selector: 'app-product-filters',
    template: '',
    standalone: true
})
class ProductFiltersStubComponent {
}

@Directive({
    selector: '[appInfiniteScroll]',
    standalone: true
})
class InfiniteScrollStubDirective {
}

@Component({
    selector: 'app-marketplace-status',
    template: '',
    standalone: true,
    inputs: ['listings']
})
class MarketplaceStatusStubComponent {
}

// @todo: Fix tests due to complex component dependencies with Dialog and Filters
describe('ProductList', () => {
    let component: ProductList;
    let fixture: ComponentFixture<ProductList>;
    let productServiceMock: MockedObject<ProductService>;
    let dialogMock: MockedObject<MatDialog>;
    let batchOperationsServiceMock: MockedObject<BatchOperationsService>;
    let notificationServiceMock: MockedObject<NotificationService>;
    let comparisonServiceMock: MockedObject<ProductComparisonService>;
    let productsSubject: BehaviorSubject<Product[]>;

    const mockProducts: Product[] = [
        {
            id: 1,
            name: 'Product 1',
            sku: 'P001',
            description: '',
            default_resale_price: 10,
            cost_price: 5,
            is_bundle: false,
            images: [
                { id: 1, product_id: 1, image_path: 'product1.jpg', is_primary: 1 },
                { id: 2, product_id: 1, image_path: 'product1-alt.jpg', is_primary: 0 }
            ],
            primary_image: { id: 1, product_id: 1, image_path: 'product1.jpg', is_primary: 1 },
            inventory_items: [{ id: 1, product_id: 1, location: 'default', quantity: 50 }],
            inventory_adjustments: [],
            custom_fields: []
        },
        {
            id: 2,
            name: 'Product 2',
            sku: 'P002',
            description: '',
            default_resale_price: 20,
            cost_price: 10,
            is_bundle: false,
            images: [
                { id: 3, product_id: 2, image_path: 'product2.jpg', is_primary: 1 }
            ],
            primary_image: { id: 3, product_id: 2, image_path: 'product2.jpg', is_primary: 1 },
            inventory_items: [],
            inventory_adjustments: [],
            custom_fields: []
        },
        {
            id: 3,
            name: 'Product 3',
            sku: 'P003',
            description: '',
            default_resale_price: 30,
            cost_price: 15,
            is_bundle: false,
            images: [],
            primary_image: undefined,
            inventory_items: [],
            inventory_adjustments: [],
            custom_fields: []
        }
    ];

    const mockPaginatedProducts: PaginatedProducts = {
        data: mockProducts,
        currentPage: 1,
        totalPages: 1,
        totalItems: 3,
        pageSize: 10,
        hasNextPage: false,
        hasPrevPage: false
    };

    beforeEach(async () => {
        productsSubject = new BehaviorSubject<Product[]>([]);
        productServiceMock = {
            getProducts: vi.fn().mockName("ProductService.getProducts"),
            deleteProduct: vi.fn().mockName("ProductService.deleteProduct")
        } as any;
        Object.defineProperty(productServiceMock, 'products$', {
            get: () => productsSubject.asObservable()
        });

        dialogMock = {
            open: vi.fn().mockName("MatDialog.open")
        } as any;
        batchOperationsServiceMock = {
            batchUpdatePrices: vi.fn().mockName("BatchOperationsService.batchUpdatePrices"),
            batchUpdateCategories: vi.fn().mockName("BatchOperationsService.batchUpdateCategories"),
            batchUpdateCustomFields: vi.fn().mockName("BatchOperationsService.batchUpdateCustomFields")
        } as any;
        notificationServiceMock = {
            showSuccess: vi.fn().mockName("NotificationService.showSuccess"),
            showError: vi.fn().mockName("NotificationService.showError")
        } as any;
        comparisonServiceMock = {
            isInComparison: vi.fn().mockName("ProductComparisonService.isInComparison"),
            toggleProductInComparison: vi.fn().mockName("ProductComparisonService.toggleProductInComparison"),
            getProducts: vi.fn().mockName("ProductComparisonService.getProducts")
        } as any;

        await TestBed.configureTestingModule({
            imports: [
                ProductList,
                NoopAnimationsModule,
                HttpClientTestingModule,
                HttpClientTestingModule,
                RouterTestingModule,
                TranslocoTestingModule.forRoot({
                    langs: { en: {}, es: {} },
                    translocoConfig: { availableLangs: ['en', 'es'], defaultLang: 'en' }
                })
            ],
            providers: [
                { provide: ProductService, useValue: productServiceMock },
                { provide: MatDialog, useValue: dialogMock },
                { provide: BatchOperationsService, useValue: batchOperationsServiceMock },
                { provide: NotificationService, useValue: notificationServiceMock },
                { provide: ProductComparisonService, useValue: comparisonServiceMock }
            ],
            schemas: [NO_ERRORS_SCHEMA]
        })
            .overrideComponent(ProductList, {
                remove: {
                    imports: [
                        SharedModule,
                        ProductForm,
                        BatchActionToolbarComponent,
                        PaginationComponent,
                        ProductFiltersComponent,
                        InfiniteScrollStubDirective,
                        MatButtonModule,
                        MatIconModule,
                        MatCardModule,
                        MatCheckboxModule,
                        MatSidenavModule,
                        MatProgressSpinnerModule,
                        MatTooltipModule,
                        MatMenuModule,
                        MatDividerModule,
                        // CommonModule, // Keep CommonModule for pipes
                        // FormsModule, // Keep for ngModel in filters
                        RouterModule,
                        MarketplaceStatusComponent,
                        AiSearchBar,
                        MatDialogModule // Ensure real dialog module is removed so mock is used
                        // MatFormFieldModule, // Keep for filters
                        // MatSelectModule, // Keep for filters
                        // MatInputModule // Keep for filters
                    ]
                },
                add: {
                    imports: [
                        AiSearchBarStubComponent,
                        ProductFormStubComponent,
                        BatchActionToolbarStubComponent,
                        PaginationStubComponent,
                        ProductFiltersStubComponent,
                        InfiniteScrollStubDirective,
                        MarketplaceStatusStubComponent,
                        CommonModule,
                        MatMenuModule,
                        MatButtonModule
                    ],
                    schemas: [NO_ERRORS_SCHEMA]
                }
            })
            .compileComponents();

        fixture = TestBed.createComponent(ProductList);
        component = fixture.componentInstance;

        // Provide default mock for dialog.open to avoid crashes
        dialogMock.open.mockReturnValue({ afterClosed: () => of(false) } as any);

        // Provide default mock for getProducts to avoid crash in ngOnInit -> loadProducts
        productServiceMock.getProducts.mockReturnValue(of(mockPaginatedProducts));

        fixture.detectChanges();
    });

    afterEach(() => {
        fixture.destroy();
    });

    it('should create the component', () => {
        expect(component).toBeTruthy();
    });

    it('should call getProducts on init and subscribe to products$', () => {
        productServiceMock.getProducts.mockReturnValue(of(mockPaginatedProducts));

        fixture.detectChanges(); // ngOnInit

        expect(productServiceMock.getProducts).toHaveBeenCalled();

        // The subscription to products$ will update the data
        productsSubject.next(mockProducts);
        expect(component.products).toEqual(mockProducts);
    });

    describe('deleteProduct', () => {
        it('should open confirmation dialog', () => {
            dialogMock.open.mockReturnValue({ afterClosed: () => of(false) } as any);
            component.deleteProduct(1);
            expect(dialogMock.open).toHaveBeenCalled();
        });

        it('should call productService.deleteProduct if dialog is confirmed', () => {
            dialogMock.open.mockReturnValue({ afterClosed: () => of(true) } as any);
            productServiceMock.deleteProduct.mockReturnValue(of(null));

            component.deleteProduct(1);

            expect(productServiceMock.deleteProduct).toHaveBeenCalledWith(1);
        });

        it('should NOT call productService.deleteProduct if dialog is dismissed', () => {
            dialogMock.open.mockReturnValue({ afterClosed: () => of(false) } as any);

            component.deleteProduct(1);

            expect(productServiceMock.deleteProduct).not.toHaveBeenCalled();
        });
    });

    describe('image handling', () => {
        beforeEach(() => {
            productServiceMock.getProducts.mockReturnValue(of(mockPaginatedProducts));
            fixture.detectChanges(); // Initialize with mock products
        });

        it('should get primary image when primary image exists', () => {
            const productWithPrimary = mockProducts[0];
            const primaryImagePath = component.getPrimaryImage(productWithPrimary);
            expect(primaryImagePath).toBe('product1.jpg');
        });

        it('should get first image when no primary image exists', () => {
            const productWithoutPrimary = { ...mockProducts[0] } as any;
            productWithoutPrimary.primary_image = undefined; // No primary image
            const imagePath = component.getPrimaryImage(productWithoutPrimary);
            expect(imagePath).toBe('product1.jpg'); // First image in the array
        });

        it('should return placeholder when no images exist', () => {
            const productWithoutImages = mockProducts[2]; // Product with no images
            const imagePath = component.getPrimaryImage(productWithoutImages);
            expect(imagePath).toBe('placeholder.jpg');
        });

        it('should format image URL correctly', () => {
            const imagePath = 'test.jpg';
            const formattedUrl = component.getImageUrl(imagePath);
            expect(formattedUrl).toBe('/uploads/product_images/test.jpg');
        });

        it('should handle image errors by setting placeholder', () => {
            const mockEvent = {
                target: { src: 'original.jpg' }
            } as any;
            component.onImageError(mockEvent);
            expect(mockEvent.target.src).toContain('data:image');
        });
    });

    describe('stock display', () => {
        it('should calculate stock correctly for product with default location', () => {
            const product = {
                ...mockProducts[0],
                inventory_items: [
                    { id: 1, product_id: 1, location: 'default', quantity: 50 },
                    { id: 2, product_id: 1, location: 'warehouse', quantity: 20 }
                ]
            };
            expect(component.getCurrentStock(product)).toBe(50);
        });

        it('should calculate stock correctly for product without default location (sum all)', () => {
            const product = {
                ...mockProducts[0],
                inventory_items: [
                    { id: 1, product_id: 1, location: 'store', quantity: 10 },
                    { id: 2, product_id: 1, location: 'warehouse', quantity: 20 }
                ]
            };
            expect(component.getCurrentStock(product)).toBe(30);
        });

        it('should return 0 stock for product with no inventory items', () => {
            const product = { ...mockProducts[0], inventory_items: [] };
            expect(component.getCurrentStock(product)).toBe(0);
        });

        it('should display stock count in product card', () => {
            const productWithStock = {
                ...mockProducts[0],
                inventory_items: [{ id: 1, product_id: 1, location: 'default', quantity: 42 }],
                stock_quantity: 42
            };

            const paginatedWithStock = { ...mockPaginatedProducts, data: [productWithStock] };
            productServiceMock.getProducts.mockReturnValue(of(paginatedWithStock));

            component.viewMode = 'grid'; // Switch to grid view to render cards
            component.loadProducts();
            fixture.detectChanges();

            const compiled = fixture.nativeElement;
            const stockElement = compiled.querySelector('.stock');
            // Expect "42 " because "inStock" key isn't translated in mock config, or returns key
            // The template is "{{ product.stock_quantity }} {{ t('products.stockStatus.inStock') }}"
            expect(stockElement.textContent).toContain('42');
        });
    });

    describe('loadProducts functionality', () => {
        it('should load products with pagination', () => {
            const mockPaginatedResponse: PaginatedProducts = {
                data: mockProducts,
                currentPage: 1,
                totalPages: 1,
                totalItems: 3,
                pageSize: 10,
                hasNextPage: false,
                hasPrevPage: false
            };

            productServiceMock.getProducts.mockReturnValue(of(mockPaginatedResponse));
            component.loadProducts(1, 10);

            expect(productServiceMock.getProducts).toHaveBeenCalledWith(1, 10, {});
            expect(component.products).toEqual(mockProducts);
        });
    });
});
