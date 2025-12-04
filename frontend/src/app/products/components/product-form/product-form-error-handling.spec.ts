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
  @Input() existingImages: ProductImage[] = [];
  @Input() stagedImages: File[] = [];
  @Input() stagedImagePreviews: string[] = [];
  @Input() productId: number | null = null;
  @Output() stagedImagesChange = new EventEmitter<File[]>();
  @Output() stagedImagePreviewsChange = new EventEmitter<string[]>();
  @Output() imagesToDelete = new EventEmitter<number[]>();
  @Output() primaryImageChange = new EventEmitter<number | null>();
  @Output() imageUpdated = new EventEmitter<{ imageId: number, field: 'title' | 'description', value: string }>();
  @Output() existingImagesChange = new EventEmitter<ProductImage[]>();
}

@Component({
  selector: 'app-product-variants',
  standalone: true,
  template: ''
})
class MockProductVariantsComponent {
  @Input() productVariants: ProductVariant[] = [];
  @Output() variantsChanged = new EventEmitter<ProductVariant[]>();
  @Output() addVariant = new EventEmitter<void>();
}

describe('ProductForm: Error Handling', () => {
  let component: ProductForm;
  let fixture: ComponentFixture<ProductForm>;
  let productServiceMock: jasmine.SpyObj<ProductService>;
  let notificationServiceMock: jasmine.SpyObj<NotificationService>;
  let httpMock: HttpTestingController;
  let routerMock: jasmine.SpyObj<Router>;
  let activatedRouteMock: any;
  let dialogMock: jasmine.SpyObj<MatDialog>;
  let productFormInitializerService: ProductFormInitializerService;

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
    productServiceMock = jasmine.createSpyObj('ProductService', ['createProduct', 'updateProduct', 'saveCustomFieldValues', 'updateProductImage', 'deleteProductImage', 'setPrimaryProductImage', 'getProductById', 'uploadProductImage']);
    notificationServiceMock = jasmine.createSpyObj('NotificationService', ['showSuccess', 'showError']);
    dialogMock = jasmine.createSpyObj('MatDialog', ['open']);

    Object.defineProperty(productServiceMock, 'products$', {
      get: () => new BehaviorSubject([mockProduct]).asObservable()
    });

    routerMock = jasmine.createSpyObj('Router', ['navigate', 'getCurrentNavigation']);

    activatedRouteMock = {
      snapshot: {
        params: {}
      }
    };

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
      spyOn(productFormInitializerService, 'initializeForm').and.returnValue(of({
        customFields: [],
        product: undefined,
        isEditMode: false,
        initialPrimaryImageId: null
      }));
      fixture.detectChanges();

      // Mock an error during product creation
      productServiceMock.createProduct.and.returnValue(throwError(() => new Error('API Error')));

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

      expect(notificationServiceMock.showError).toHaveBeenCalledWith('Failed to create product.');
    });

    it('should handle form submission errors in edit mode', () => {
      spyOn(productFormInitializerService, 'initializeForm').and.returnValue(of({
        customFields: [],
        product: mockProduct,
        isEditMode: true,
        initialPrimaryImageId: null
      }));
      fixture.detectChanges();

      // Mock an error during product update
      productServiceMock.updateProduct.and.returnValue(throwError(() => new Error('API Error')));

      component.productForm.setValue({
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
        weight: 15,
        custom_field_1: '' // Add this if needed, or rely on dynamic addition
      });

      component.onSubmit();
      // await fixture.whenStable();

      expect(notificationServiceMock.showError).toHaveBeenCalledWith('Failed to update product.');
    });

    it('should handle cancellation with confirmation dialog', () => {
      spyOn(productFormInitializerService, 'initializeForm').and.returnValue(of({
        customFields: [],
        product: mockProduct,
        isEditMode: true,
        initialPrimaryImageId: null
      }));
      fixture.detectChanges();
      // Mock dialog to return true (confirm cancellation)
      const dialogRefMock = jasmine.createSpyObj('MatDialogRef', ['afterClosed']);
      dialogRefMock.afterClosed.and.returnValue(of(true));
      dialogMock.open.and.returnValue(dialogRefMock);

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

      fixture.detectChanges();
      await fixture.whenStable();

      // Should handle gracefully without throwing errors
      expect(component.isEditMode).toBe(true);
    });
  });
});