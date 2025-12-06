import { TestBed, ComponentFixture, fakeAsync, tick, waitForAsync } from '@angular/core/testing';
import { NO_ERRORS_SCHEMA } from '@angular/core';
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

xdescribe('ProductForm: Edit Mode', () => {
  let component: ProductForm;
  let fixture: ComponentFixture<ProductForm>;
  let productServiceMock: jasmine.SpyObj<ProductService>;
  let notificationServiceMock: jasmine.SpyObj<NotificationService>;
  let httpMock: HttpTestingController;
  let routerMock: jasmine.SpyObj<Router>;
  let activatedRouteMock: any;
  let dialogMock: jasmine.SpyObj<MatDialog>;
  let productFormInitializerMock: jasmine.SpyObj<ProductFormInitializerService>;
  let customFieldServiceMock: jasmine.SpyObj<CustomFieldService>;

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
    productServiceMock = jasmine.createSpyObj('ProductService', ['createProduct', 'updateProduct', 'saveCustomFieldValues', 'updateProductImage', 'deleteProductImage', 'setPrimaryProductImage', 'uploadProductImage', 'getProducts']);
    notificationServiceMock = jasmine.createSpyObj('NotificationService', ['showSuccess']);
    dialogMock = jasmine.createSpyObj('MatDialog', ['open']);
    productFormInitializerMock = jasmine.createSpyObj('ProductFormInitializerService', ['initializeForm']);
    customFieldServiceMock = jasmine.createSpyObj('CustomFieldService', ['getCustomFields']);

    // Create a mock ProductService with a BehaviorSubject that immediately emits
    const mockProductsSubject = new BehaviorSubject<Product[]>([mockProduct]);
    Object.defineProperty(productServiceMock, 'products$', {
      get: () => mockProductsSubject.asObservable()
    });

    routerMock = jasmine.createSpyObj('Router', ['navigate', 'getCurrentNavigation']);

    activatedRouteMock = {
      snapshot: {
        params: {}
      }
    };

    // Set up the initializer mock to return synchronous data for edit mode
    productFormInitializerMock.initializeForm.and.returnValue(of({
      customFields: [],
      product: mockProduct,
      isEditMode: true,
      initialPrimaryImageId: null
    }));

    // Mock params for edit mode
    activatedRouteMock = {
      snapshot: {
        params: { id: '1' }
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
        { provide: ProductFormInitializerService, useValue: productFormInitializerMock },
        { provide: CustomFieldService, useValue: customFieldServiceMock }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    })
      .overrideComponent(ProductForm, {
        set: {
          imports: [
            CommonModule,
            ReactiveFormsModule,
            MatFormFieldModule,
            MatInputModule,
            MatCardModule,
            MatButtonModule,
            MatIconModule,
            MatListModule
          ],
          schemas: [NO_ERRORS_SCHEMA]
        }
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

  describe('Edit Mode', () => {
    it('should initialize in edit mode', () => {
      fixture.detectChanges();

      expect(component.isEditMode).toBeTrue();
      expect(component.productId).toBe(1);
      expect(component.productForm.get('name')?.value).toBe(mockProduct.name);
    });

    it('should call updateProduct on submit', () => {
      fixture.detectChanges();

      productServiceMock.updateProduct.and.returnValue(of(mockProduct));
      productServiceMock.saveCustomFieldValues.and.returnValue(of({}));

      component.productForm.setValue({
        name: 'Updated',
        sku: 'T001',
        description: '',
        default_resale_price: 120,
        cost_price: 60,
        manufacturer: 'Updated Manufacturer',
        brand: 'Updated Brand',
        category: 'Updated Category',
        width: 12,
        height: 12,
        depth: 12,
        weight: 12,
      });

      component.onSubmit();

      expect(productServiceMock.updateProduct).toHaveBeenCalled();
      expect(routerMock.navigate).toHaveBeenCalledWith(['/products']);
    });
  });
});