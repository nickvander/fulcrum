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
import { of, BehaviorSubject } from 'rxjs';
import { Product } from '../../models/product.model';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatListModule } from '@angular/material/list';
import { MatDialog } from '@angular/material/dialog';
import { ImageDialogComponent } from '../../../shared/components/image-dialog/image-dialog';
import { ConfirmationDialog } from '../../../shared/components/confirmation-dialog/confirmation-dialog';

import { CustomFieldService } from '../../../settings/services/custom-field.service';
import { environment } from '../../../../environments/environment';

import { NotificationService } from '../../../core/services/notification.service';
import { ProductFormInitializerService } from '../../services/product-form-initializer.service';
import { ProductFormInitializerServiceMock } from '../../services/product-form-initializer.service.mock';

describe('ProductForm: Image Management', () => {
    let component: ProductForm;
    let fixture: ComponentFixture<ProductForm>;
    let productServiceMock: MockedObject<ProductService>;
    let notificationServiceMock: MockedObject<NotificationService>;
    let httpMock: HttpTestingController;
    let routerMock: MockedObject<Router>;
    let activatedRouteMock: any;
    let dialogMock: MockedObject<MatDialog>;
    let productFormInitializerMock: MockedObject<ProductFormInitializerService>;

    const mockProduct: Product = {
        id: 1,
        name: 'Test Product',
        sku: 'T001',
        description: '',
        default_resale_price: 100,
        cost_price: 50,
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
            uploadProductImage: vi.fn().mockName("ProductService.uploadProductImage"),
            getProductById: vi.fn().mockName("ProductService.getProductById")
        } as any;
        notificationServiceMock = {
            showSuccess: vi.fn().mockName("NotificationService.showSuccess")
        } as any;
        dialogMock = {
            open: vi.fn().mockName("MatDialog.open")
        } as any;
        productFormInitializerMock = {
            initializeForm: vi.fn().mockName("ProductFormInitializerService.initializeForm")
        } as any;

        // Create a mock ProductService with a BehaviorSubject that immediately emits
        const mockProductsSubject = new BehaviorSubject<Product[]>([mockProduct]);
        Object.defineProperty(productServiceMock, 'products$', {
            get: () => mockProductsSubject.asObservable()
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

        // Set up the initializer mock to return synchronous data for edit mode
        productFormInitializerMock.initializeForm.mockReturnValue(of({
            customFields: [],
            product: mockProduct,
            isEditMode: true,
            initialPrimaryImageId: null
        }));

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
                CustomFieldService,
                { provide: Router, useValue: routerMock },
                { provide: ActivatedRoute, useValue: activatedRouteMock },
                { provide: ProductFormInitializerService, useClass: ProductFormInitializerServiceMock }
            ]
        })
            .compileComponents();

        fixture = TestBed.createComponent(ProductForm);
        component = fixture.componentInstance;
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
        httpMock.verify();
    });

    it('should create the component', () => {
        expect(component).toBeTruthy();
    });

    it('should navigate to /products on cancel', () => {
        component.onCancel();
        expect(routerMock.navigate).toHaveBeenCalledWith(['/products']);
    });

    describe('image handling', () => {
        beforeEach(() => {
            // These tests require the component to be in "edit mode"
            activatedRouteMock.snapshot.params['id'] = mockProduct.id;
            routerMock.getCurrentNavigation.mockReturnValue(null);
            // Mock the getProductById method to return an observable with the mock product
            productServiceMock.getProductById.mockReturnValue(of(mockProduct));
            fixture.detectChanges();
        });

        it('should format image URL correctly', () => {
            const imagePath = 'test.jpg';
            const formattedUrl = component.getImageUrl(imagePath);
            expect(formattedUrl).toBe('/uploads/product_images/test.jpg');
        });

        // Removed specific image handling tests since they are now in the child component
    });
});
