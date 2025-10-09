import { TestBed, ComponentFixture } from '@angular/core/testing';
import { ProductForm } from './product-form';
import { RouterTestingModule } from '@angular/router/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router } from '@angular/router';
import { ProductService } from '../../services/product';
import { of, BehaviorSubject } from 'rxjs';
import { Product } from '../../models/product.model';

describe('ProductForm', () => {
  let component: ProductForm;
  let fixture: ComponentFixture<ProductForm>;
  let productServiceMock: jasmine.SpyObj<ProductService>;
  let routerMock: jasmine.SpyObj<Router>;
  let activatedRouteMock: any;

  const mockProduct: Product = { id: 1, name: 'Test Product', sku: 'T001', description: '', default_resale_price: 100 };

  beforeEach(async () => {
    productServiceMock = jasmine.createSpyObj('ProductService', ['createProduct', 'updateProduct']);
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
        NoopAnimationsModule
      ],
      providers: [
        { provide: ProductService, useValue: productServiceMock },
        { provide: Router, useValue: routerMock },
        { provide: ActivatedRoute, useValue: activatedRouteMock }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ProductForm);
    component = fixture.componentInstance;
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  describe('Create Mode', () => {
    beforeEach(() => {
      routerMock.getCurrentNavigation.and.returnValue(null);
      fixture.detectChanges();
    });

    it('should initialize an empty form', () => {
      expect(component.isEditMode).toBeFalse();
      expect(component.productForm.value.name).toBe('');
    });

    it('should call createProduct on submit', () => {
      productServiceMock.createProduct.and.returnValue(of(mockProduct));
      component.productForm.setValue({ name: 'New', sku: 'N001', description: '', default_resale_price: 10 });
      component.onSubmit();
      expect(productServiceMock.createProduct).toHaveBeenCalled();
      expect(routerMock.navigate).toHaveBeenCalledWith(['/products']);
    });

    it('should pre-fill form from navigation state', () => {
        const navigationState = { extras: { state: { productData: { name: 'AI Product' } } } };
        routerMock.getCurrentNavigation.and.returnValue(navigationState as any);
        component.ngOnInit();
        expect(component.productForm.value.name).toBe('AI Product');
      });
  });

  describe('Edit Mode', () => {
    beforeEach(() => {
      activatedRouteMock.snapshot.params['id'] = mockProduct.id;
      routerMock.getCurrentNavigation.and.returnValue(null);
      fixture.detectChanges();
    });

    it('should initialize the form with product data', () => {
      expect(component.isEditMode).toBeTrue();
      expect(component.productForm.value.name).toBe(mockProduct.name);
    });

    it('should call updateProduct on submit', () => {
      productServiceMock.updateProduct.and.returnValue(of(mockProduct));
      component.productForm.setValue({ name: 'Updated', sku: 'T001', description: '', default_resale_price: 120 });
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
