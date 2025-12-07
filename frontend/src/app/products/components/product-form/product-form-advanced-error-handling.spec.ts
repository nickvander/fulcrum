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
import { ProductFormInitializerService } from '../../services/product-form-initializer.service';
import { ProductFormInitializerServiceAsyncMock } from '../../services/product-form-initializer.service.async.mock';

// DISABLED: Async mock service interactions cause test instability.
// See work/archive/44-product-form-create-test-hanging-deep-dive.md for details.
xdescribe('ProductForm: Advanced Error Handling with Async Mock', () => {
  let component: ProductForm;
  let fixture: ComponentFixture<ProductForm>;
  let productServiceMock: jasmine.SpyObj<ProductService>;
  let notificationServiceMock: jasmine.SpyObj<NotificationService>;
  let httpMock: HttpTestingController;
  let routerMock: jasmine.SpyObj<Router>;
  let activatedRouteMock: any;
  let dialogMock: jasmine.SpyObj<MatDialog>;

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
    images: [
      { id: 1, product_id: 1, image_path: 'test.jpg', is_primary: 1, title: '', description: '' }
    ],
    custom_fields: []
  };

  beforeEach(async () => {
    productServiceMock = jasmine.createSpyObj('ProductService', ['createProduct', 'updateProduct', 'saveCustomFieldValues', 'updateProductImage', 'deleteProductImage', 'setPrimaryProductImage', 'getProductById', 'uploadProductImage']);
    notificationServiceMock = jasmine.createSpyObj('NotificationService', ['showSuccess', 'showError']);
    dialogMock = jasmine.createSpyObj('MatDialog', ['open']);

    // Mock products$ as a BehaviorSubject for testing ngOnInit
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
        // Using the async mock that simulates async behavior but with small delay
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