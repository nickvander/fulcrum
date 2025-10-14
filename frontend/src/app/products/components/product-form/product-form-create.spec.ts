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

describe('ProductForm: Create Mode', () => {
  let component: ProductForm;
  let fixture: ComponentFixture<ProductForm>;
  let productServiceMock: jasmine.SpyObj<ProductService>;
  let notificationServiceMock: jasmine.SpyObj<NotificationService>;
  let httpMock: HttpTestingController;
  let routerMock: jasmine.SpyObj<Router>;
  let activatedRouteMock: any;
  let dialogMock: jasmine.SpyObj<MatDialog>;
  let productFormInitializerMock: jasmine.SpyObj<ProductFormInitializerService>;

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

    // Set up the initializer mock to return synchronous data for create mode
    productFormInitializerMock.initializeForm.and.returnValue(of({
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

  xdescribe('Create Mode', () => {
    beforeEach(() => {
      routerMock.getCurrentNavigation.and.returnValue(null);
    });

    it('should initialize an empty form', () => {
      fixture.detectChanges();
      const req = httpMock.expectOne(`${environment.apiUrl}/custom-fields`);
      req.flush([]);
      expect(component.isEditMode).toBeFalse();
      expect(component.productForm.value.name).toBe('');
    });

    it('should call createProduct on submit', async () => {
      fixture.detectChanges();
      const req = httpMock.expectOne(`${environment.apiUrl}/custom-fields`);
      req.flush([]);
      productServiceMock.createProduct.and.returnValue(of(mockProduct));
      productServiceMock.saveCustomFieldValues.and.returnValue(of({}));
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
      productServiceMock.createProduct.and.returnValue(of(mockProduct));
      productServiceMock.saveCustomFieldValues.and.returnValue(of({}));
      
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
      
      productServiceMock.createProduct.and.returnValue(of(mockProduct));
      productServiceMock.saveCustomFieldValues.and.returnValue(of({}));
      productServiceMock.uploadProductImage.and.returnValue(of({ id: 1, product_id: 1, image_path: 'test.jpg', is_primary: 0, title: '', description: '' }));
      
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
      
      expect(component.isDirty).toBeFalse();
      
      // Add a staged image
      component.stagedImages.push(new File([], 'test.jpg'));
      
      expect(component.isDirty).toBeTrue();
    });

    it('should pre-fill form from navigation state', async () => {
        const navigationState = { extras: { state: { productData: { name: 'AI Product' } } } };
        routerMock.getCurrentNavigation.and.returnValue(navigationState as any);
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