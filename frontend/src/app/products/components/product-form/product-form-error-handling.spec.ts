import type { MockedObject } from "vitest";
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { CommonModule } from '@angular/common';
import { ProductForm } from './product-form';
import { RouterTestingModule } from '@angular/router/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router } from '@angular/router';
import { ProductService } from '../../services/product';
import { of, BehaviorSubject, throwError } from 'rxjs';
import { Product, ProductImage, ProductVariant } from '../../models/product.model';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatListModule } from '@angular/material/list';
import { MatDialog } from '@angular/material/dialog';
import { NotificationService } from '../../../core/services/notification.service';
import { ProductFormInitializerService } from '../../services/product-form-initializer.service';
import { ProductFormInitializerServiceMock } from '../../services/product-form-initializer.service.mock';
import { Component, Input, Output, EventEmitter } from '@angular/core';
import { ProductFormImageGalleryComponent } from './product-form-image-gallery.component';
import { ProductVariantsComponent } from '../product-variants/product-variants';

// Mock Child Components
@Component({
    selector: 'app-product-form-image-gallery',
    standalone: true,
    template: ''
})
class MockProductFormImageGalleryComponent {
    @Input()
    existingImages: ProductImage[] = [];
    @Input()
    stagedImages: File[] = [];
    @Input()
    stagedImagePreviews: string[] = [];
    @Input()
    productId: number | null = null;
    @Output()
    stagedImagesChange = new EventEmitter<File[]>();
    @Output()
    stagedImagePreviewsChange = new EventEmitter<string[]>();
    @Output()
    imagesToDelete = new EventEmitter<number[]>();
    @Output()
    primaryImageChange = new EventEmitter<number | null>();
    @Output()
    imageUpdated = new EventEmitter<{
        imageId: number;
        field: 'title' | 'description';
        value: string;
    }>();
    @Output()
    existingImagesChange = new EventEmitter<ProductImage[]>();
}

@Component({
    selector: 'app-product-variants',
    standalone: true,
    template: ''
})
class MockProductVariantsComponent {
    @Input()
    productVariants: ProductVariant[] = [];
    @Output()
    variantsChanged = new EventEmitter<ProductVariant[]>();
    @Output()
    addVariant = new EventEmitter<void>();
}

// @todo: Fix productForm.setValue issue - form group structure mismatch
describe.skip('ProductForm: Error Handling', () => {
    let component: ProductForm;
    let fixture: ComponentFixture<ProductForm>;
    let productServiceMock: MockedObject<ProductService>;
    let notificationServiceMock: MockedObject<NotificationService>;
    let httpMock: HttpTestingController;
    let routerMock: MockedObject<Router>;
    let activatedRouteMock: any;
    let dialogMock: MockedObject<MatDialog>;
    let productFormInitializerService: ProductFormInitializerService;

    const mockProduct: Product = {
        id: 1,
        name: 'Test Product',
        sku: 'TEST001',
        description: 'Test Description',
        default_resale_price: 100,
        cost_price: 50,
        is_bundle: false,
        images: [],
        inventory_items: [],
        inventory_adjustments: [],
        custom_fields: [],
        manufacturer: 'Test Manufacturer',
        brand: 'Test Brand',
        category: 'Test Category',
        width: 10,
        height: 10,
        depth: 10,
        weight: 10,
    };

    beforeEach(async () => {
        productServiceMock = {
            createProduct: vi.fn().mockName("ProductService.createProduct"),
            updateProduct: vi.fn().mockName("ProductService.updateProduct"),
            saveCustomFieldValues: vi.fn().mockName("ProductService.saveCustomFieldValues"),
            updateProductImage: vi.fn().mockName("ProductService.updateProductImage"),
            deleteProductImage: vi.fn().mockName("ProductService.deleteProductImage"),
            setPrimaryProductImage: vi.fn().mockName("ProductService.setPrimaryProductImage"),
            getProductById: vi.fn().mockName("ProductService.getProductById"),
            uploadProductImage: vi.fn().mockName("ProductService.uploadProductImage")
        } as any;
        notificationServiceMock = {
            showSuccess: vi.fn().mockName("NotificationService.showSuccess"),
            showError: vi.fn().mockName("NotificationService.showError")
        } as any;
        dialogMock = {
            open: vi.fn().mockName("MatDialog.open")
        } as any;

        Object.defineProperty(productServiceMock, 'products$', {
            get: () => new BehaviorSubject([mockProduct]).asObservable()
        });

        routerMock = {
            navigate: vi.fn().mockName("Router.navigate"),
            getCurrentNavigation: vi.fn().mockName("Router.getCurrentNavigation")
        } as any;

        activatedRouteMock = {
            snapshot: {
                params: {}
            },
            queryParams: of({})
        } as any;

        await TestBed.configureTestingModule({
            imports: [
                ProductForm,
                RouterTestingModule,
                HttpClientTestingModule,
                ReactiveFormsModule,
                NoopAnimationsModule,
                CommonModule,
                MatIconModule,
                MatCardModule,
                MatFormFieldModule,
                MatInputModule,
                MatButtonModule,
                MatListModule
            ],
            providers: [
                { provide: ProductService, useValue: productServiceMock },
                { provide: NotificationService, useValue: notificationServiceMock },
                { provide: MatDialog, useValue: dialogMock },
                { provide: Router, useValue: routerMock },
                { provide: ActivatedRoute, useValue: activatedRouteMock },
                { provide: ProductFormInitializerService, useClass: ProductFormInitializerServiceMock }
            ]
        })
            .overrideComponent(ProductForm, {
                remove: { imports: [ProductFormImageGalleryComponent, ProductVariantsComponent] },
                add: { imports: [MockProductFormImageGalleryComponent, MockProductVariantsComponent] }
            })
            .compileComponents();

        fixture = TestBed.createComponent(ProductForm);
        component = fixture.componentInstance;
        httpMock = TestBed.inject(HttpTestingController);
        productFormInitializerService = TestBed.inject(ProductFormInitializerService);
    });

    afterEach(() => {
        httpMock.verify();
    });

    describe('error handling', () => {
        it('should handle form submission errors in create mode', () => {
            vi.spyOn(productFormInitializerService, 'initializeForm').mockReturnValue(of({
                customFields: [],
                product: undefined,
                isEditMode: false,
                initialPrimaryImageId: null
            }));
            fixture.detectChanges();

            // Mock an error during product creation
            productServiceMock.createProduct.mockReturnValue(throwError(() => new Error('API Error')));

            component.productForm.setValue({
                name: 'New Product',
                sku: 'NP001',
                description: 'New Product Description',
                default_resale_price: 10,
                cost_price: 5,
                manufacturer: 'New Manufacturer',
                brand: 'New Brand',
                category: 'New Category',
                width: 1,
                height: 1,
                depth: 1,
                weight: 1,
            });

            component.onSubmit();
            // await fixture.whenStable();

            expect(notificationServiceMock.showError).toHaveBeenCalledWith('Error creating product');
        });

        it('should handle form submission errors in edit mode', () => {
            vi.spyOn(productFormInitializerService, 'initializeForm').mockReturnValue(of({
                customFields: [],
                product: mockProduct,
                isEditMode: true,
                initialPrimaryImageId: null
            }));
            fixture.detectChanges();

            // Mock an error during product update
            productServiceMock.updateProduct.mockReturnValue(throwError(() => new Error('API Error')));

            component.productForm.patchValue({
                name: 'Updated Product',
                sku: 'UPDATED001',
                description: 'Updated Description',
                default_resale_price: 150,
                cost_price: 75,
                manufacturer: 'Updated Manufacturer',
                brand: 'Updated Brand',
                category: 'Updated Category',
                width: 15,
                height: 15,
                depth: 15,
                weight: 15
            });

            component.onSubmit();
            // await fixture.whenStable();

            expect(notificationServiceMock.showError).toHaveBeenCalledWith('Error updating product');
        });

        it('should handle cancellation with confirmation dialog', () => {
            vi.spyOn(productFormInitializerService, 'initializeForm').mockReturnValue(of({
                customFields: [],
                product: undefined,
                isEditMode: true,
                initialPrimaryImageId: null
            }));
            fixture.detectChanges();
            // Mock dialog to return true (confirm cancellation)
            const dialogRefMock = {
                afterClosed: vi.fn().mockName("MatDialogRef.afterClosed")
            } as any;
            dialogRefMock.afterClosed.mockReturnValue(of(true));
            dialogMock.open.mockReturnValue(dialogRefMock);

            // Set up a dirty form to trigger the confirmation dialog
            component.productForm.get('name')?.setValue('Changed Value');

            component.onCancel();

            expect(routerMock.navigate).toHaveBeenCalledWith(['/products']);
        });

        it('should handle custom field fetch failures gracefully', async () => {
            // The async mock service should handle this scenario
            fixture.detectChanges();
            await fixture.whenStable();

            // Should handle gracefully without throwing errors
            expect(component).toBeTruthy();
        });

        it('should handle product fetch failures in edit mode', async () => {
            // Set up edit mode scenario
            activatedRouteMock.snapshot.params['id'] = 1;

            // Mock failure
            vi.spyOn(productFormInitializerService, 'initializeForm').mockReturnValue(throwError(() => new Error('Fetch Error')));

            fixture.detectChanges();
            await fixture.whenStable();

            // Should handle gracefully without throwing errors
            expect(component.isEditMode).toBe(true);
        });
    });
});
