import type { MockedObject } from "vitest";
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { CommonModule } from '@angular/common';
import { ProductForm } from './product-form';
import { RouterTestingModule } from '@angular/router/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
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
import { ProductFormInitializerService } from '../../services/product-form-initializer.service';
import { ProductFormInitializerServiceMock } from '../../services/product-form-initializer.service.mock';

describe('ProductForm: Edge Cases', () => {
    let component: ProductForm;
    let fixture: ComponentFixture<ProductForm>;
    let productServiceMock: MockedObject<ProductService>;
    let notificationServiceMock: MockedObject<NotificationService>;
    let routerMock: MockedObject<Router>;
    let activatedRouteMock: any;
    let dialogMock: MockedObject<MatDialog>;

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
        }).compileComponents();

        fixture = TestBed.createComponent(ProductForm);
        component = fixture.componentInstance;
    });

    describe('form validation edge cases', () => {
        it('should not submit invalid form', () => {
            fixture.detectChanges();

            // Set up an invalid form state
            const nameControl = component.productForm.get('name');
            nameControl?.setValue(''); // required field empty
            component.productForm.markAsDirty();

            component.onSubmit(); // Should not call service methods

            expect(productServiceMock.createProduct).not.toHaveBeenCalled();
            expect(productServiceMock.updateProduct).not.toHaveBeenCalled();
        });

        it('should handle cancellation without unsaved changes', () => {
            fixture.detectChanges();

            component.onCancel();

            expect(routerMock.navigate).toHaveBeenCalledWith(['/products']);
        });

        it('should maintain proper isDirty state', () => {
            fixture.detectChanges();

            // Initially not dirty
            expect(component.isDirty).toBe(false);

            // After form change, should be dirty
            component.productForm.get('name')?.setValue('New Name');
            component.productForm.markAsDirty();
            expect(component.isDirty).toBe(true);
        });
    });
});
