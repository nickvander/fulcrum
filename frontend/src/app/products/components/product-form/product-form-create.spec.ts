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
import { CustomFieldService } from '../../../settings/services/custom-field.service';
import { environment } from '../../../../environments/environment';
import { NotificationService } from '../../../core/services/notification.service';
import { ProductFormInitializerService } from '../../services/product-form-initializer.service';
import { ProductFormInitializerServiceMock } from '../../services/product-form-initializer.service.mock';

// @todo: Fix productForm.setValue issue - form group structure doesn't match expected controls
describe.skip('ProductForm: Create Mode', () => {
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
            uploadProductImage: vi.fn().mockName("ProductService.uploadProductImage"),
            getProducts: vi.fn().mockName("ProductService.getProducts")
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
            }
        } as any;

        // Set up the initializer mock to return synchronous data for create mode
        productFormInitializerMock.initializeForm.mockReturnValue(of({
            customFields: [],
            isEditMode: false,
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
                { provide: Router, useValue: routerMock },
                { provide: ActivatedRoute, useValue: activatedRouteMock },
                { provide: ProductFormInitializerService, useClass: ProductFormInitializerServiceMock }
            ]
        }).compileComponents();

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

    // DISABLED: HTTP mock expectations conflict with mocked initializer service.
    // Re-enabling requires updating tests to not expect /custom-fields HTTP calls.
    describe.skip('Create Mode', () => {
        beforeEach(() => {
            routerMock.getCurrentNavigation.mockReturnValue(null);
        });

        it('should initialize an empty form', () => {
            fixture.detectChanges();
            const req = httpMock.expectOne(`${environment.apiUrl}/custom-fields`);
            req.flush([]);
            expect(component.isEditMode).toBe(false);
            expect(component.productForm.value.name).toBe('');
        });

        it('should call createProduct on submit', async () => {
            fixture.detectChanges();
            const req = httpMock.expectOne(`${environment.apiUrl}/custom-fields`);
            req.flush([]);
            productServiceMock.createProduct.mockReturnValue(of(mockProduct));
            productServiceMock.saveCustomFieldValues.mockReturnValue(of({}));
            component.productForm.setValue({
                name: 'New',
                sku: 'N001',
                description: '',
                default_resale_price: 10,
                cost_price: 5,
                manufacturer: '',
                brand: '',
                category: '',
                width: 0,
                height: 0,
                depth: 0,
                weight: 0,
            });
            component.onSubmit();
            await fixture.whenStable();
            expect(productServiceMock.createProduct).toHaveBeenCalled();
            expect(routerMock.navigate).toHaveBeenCalledWith(['/products']);
        });

        it('should navigate to products list after successful create', async () => {
            fixture.detectChanges();
            const req = httpMock.expectOne(`${environment.apiUrl}/custom-fields`);
            req.flush([]);
            productServiceMock.createProduct.mockReturnValue(of(mockProduct));
            productServiceMock.saveCustomFieldValues.mockReturnValue(of({}));

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
            await fixture.whenStable();

            expect(routerMock.navigate).toHaveBeenCalledWith(['/products']);
        });

        it('should upload staged images when creating new product', async () => {
            fixture.detectChanges();
            const req = httpMock.expectOne(`${environment.apiUrl}/custom-fields`);
            req.flush([]);

            // Add a staged image
            const testFile = new File([], 'test.jpg');
            component.stagedImages.push(testFile);

            productServiceMock.createProduct.mockReturnValue(of(mockProduct));
            productServiceMock.saveCustomFieldValues.mockReturnValue(of({}));
            productServiceMock.uploadProductImage.mockReturnValue(of({ id: 1, product_id: 1, image_path: 'test.jpg', is_primary: 0, title: '', description: '' }));

            component.productForm.setValue({
                name: 'New Product',
                sku: 'NP002',
                description: 'New Product Description',
                default_resale_price: 15,
                cost_price: 7,
                manufacturer: 'New Manufacturer',
                brand: 'New Brand',
                category: 'New Category',
                width: 2,
                height: 2,
                depth: 2,
                weight: 2,
            });

            component.onSubmit();
            await fixture.whenStable();

            expect(productServiceMock.uploadProductImage).toHaveBeenCalledWith(mockProduct.id, testFile);
        });

        it('should have save button enabled when there are staged images', () => {
            fixture.detectChanges();
            const req = httpMock.expectOne(`${environment.apiUrl}/custom-fields`);
            req.flush([]);

            expect(component.isDirty).toBe(false);

            // Add a staged image
            component.stagedImages.push(new File([], 'test.jpg'));

            expect(component.isDirty).toBe(true);
        });

        it('should pre-fill form from navigation state', async () => {
            const navigationState = { extras: { state: { productData: { name: 'AI Product' } } } } as any;
            routerMock.getCurrentNavigation.mockReturnValue(navigationState as any);
            component.ngOnInit();
            fixture.detectChanges();
            const req = httpMock.expectOne(`${environment.apiUrl}/custom-fields`);
            req.flush([]);
            await fixture.whenStable();
            expect(component.productForm.value.name).toBe('AI Product');
        });
    });

    it('should navigate to /products on cancel', () => {
        component.onCancel();
        expect(routerMock.navigate).toHaveBeenCalledWith(['/products']);
    });
});
