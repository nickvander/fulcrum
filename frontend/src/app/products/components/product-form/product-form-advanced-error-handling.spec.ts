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
import { NotificationService } from '../../../core/services/notification.service';
import { AiService } from '../../../core/services/ai.service';
import { ProductFormInitializerService } from '../../services/product-form-initializer.service';
import { ProductFormInitializerServiceAsyncMock } from '../../services/product-form-initializer.service.async.mock';
import { TranslocoTestingModule } from '@ngneat/transloco';

describe('ProductForm: Advanced Error Handling with Async Mock', () => {
    let component: ProductForm;
    let fixture: ComponentFixture<ProductForm>;
    let productServiceMock: MockedObject<ProductService>;
    let notificationServiceMock: MockedObject<NotificationService>;
    let httpMock: HttpTestingController;
    let routerMock: MockedObject<Router>;
    let activatedRouteMock: any;
    let dialogMock: MockedObject<MatDialog>;

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
        custom_fields: []
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
            uploadProductImage: vi.fn().mockName("ProductService.uploadProductImage"),
            generateUniqueSku: vi.fn().mockReturnValue("SKU-MOCK-1"),
            generateBarcodeFromSku: vi.fn().mockReturnValue("BARCODE-MOCK-1"),
        } as any;
        notificationServiceMock = {
            showSuccess: vi.fn().mockName("NotificationService.showSuccess"),
            showError: vi.fn().mockName("NotificationService.showError")
        } as any;
        dialogMock = {
            open: vi.fn().mockName("MatDialog.open")
        } as any;

        // Mock products$ as a BehaviorSubject for testing ngOnInit
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
            queryParams: of({}),
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
                MatListModule,
                TranslocoTestingModule.forRoot({ langs: { en: {}, 'es-MX': {} } }),
            ],
            providers: [
                { provide: ProductService, useValue: productServiceMock },
                { provide: NotificationService, useValue: notificationServiceMock },
                { provide: MatDialog, useValue: dialogMock },
                { provide: Router, useValue: routerMock },
                { provide: ActivatedRoute, useValue: activatedRouteMock },
                // Using the async mock that simulates async behavior but with small delay
                { provide: AiService, useValue: { isReady$: () => of(true), getCapabilities: () => of({ ready: true, enabled: true, configured: true, provider: 'google' }), invalidateCapabilities: () => {} } },
                { provide: ProductFormInitializerService, useClass: ProductFormInitializerServiceAsyncMock }
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(ProductForm);
        component = fixture.componentInstance;
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
        httpMock.verify();
    });

    describe('async behavior with realistic timing', () => {
        it('should handle initialization with async mock service', async () => {
            fixture.detectChanges();
            await fixture.whenStable();

            expect(component).toBeTruthy();
            expect(component.isEditMode).toBe(false); // Since no ID param provided
        });

        it('should handle edit mode with async mock service', async () => {
            // Setup edit mode
            activatedRouteMock.snapshot.params['id'] = mockProduct.id;

            fixture.detectChanges();
            await fixture.whenStable();

            expect(component.isEditMode).toBe(true);
        });
    });
});
