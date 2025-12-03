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
import { ProductFormInitializerServiceMock } from '../../services/product-form-initializer.service.mock';

describe('ProductForm: Edit Mode', () => {
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
    productServiceMock = jasmine.createSpyObj('ProductService', ['createProduct', 'updateProduct', 'saveCustomFieldValues', 'updateProductImage', 'deleteProductImage', 'setPrimaryProductImage', 'getProductById']);
    notificationServiceMock = jasmine.createSpyObj('NotificationService', ['showSuccess']);
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
        { provide: ProductFormInitializerService, useClass: ProductFormInitializerServiceMock }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ProductForm);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
    productFormInitializerService = TestBed.inject(ProductFormInitializerService);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  describe('Edit Mode', () => {
    beforeEach(() => {
      activatedRouteMock.snapshot.params['id'] = mockProduct.id;
      routerMock.getCurrentNavigation.and.returnValue(null);
    });

    it('should initialize the form with product data', () => {
      spyOn(productFormInitializerService, 'initializeForm').and.returnValue(of({
        customFields: [],
        product: mockProduct,
        isEditMode: true,
        initialPrimaryImageId: null
      }));
      fixture.detectChanges();
      expect(component.isEditMode).toBeTrue();
      expect(component.productForm.value.name).toBe(mockProduct.name);
    });

    it('should call updateProduct on submit', () => {
      spyOn(productFormInitializerService, 'initializeForm').and.returnValue(of({
        customFields: [],
        product: mockProduct,
        isEditMode: true,
        initialPrimaryImageId: null
      }));
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

  it('should navigate to /products on cancel', () => {
    component.onCancel();
    expect(routerMock.navigate).toHaveBeenCalledWith(['/products']);
  });
});