import { TestBed, ComponentFixture } from '@angular/core/testing';
import { ProductList } from './product-list';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { ProductService } from '../../services/product';
import { MatDialog } from '@angular/material/dialog';
import { of, BehaviorSubject } from 'rxjs';
import { Product } from '../../models/product.model';

describe('ProductList', () => {
  let component: ProductList;
  let fixture: ComponentFixture<ProductList>;
  let productServiceMock: jasmine.SpyObj<ProductService>;
  let dialogMock: jasmine.SpyObj<MatDialog>;
  let productsSubject: BehaviorSubject<Product[]>;

  const mockProducts: Product[] = [
    { id: 1, name: 'Product 1', sku: 'P001', description: '', default_resale_price: 10 },
    { id: 2, name: 'Product 2', sku: 'P002', description: '', default_resale_price: 20 },
  ];

  beforeEach(async () => {
    productsSubject = new BehaviorSubject<Product[]>([]);
    productServiceMock = jasmine.createSpyObj('ProductService', ['getProducts', 'deleteProduct']);
    Object.defineProperty(productServiceMock, 'products$', {
      get: () => productsSubject.asObservable()
    });

    dialogMock = jasmine.createSpyObj('MatDialog', ['open']);

    await TestBed.configureTestingModule({
      imports: [
        ProductList,
        NoopAnimationsModule,
        HttpClientTestingModule,
        RouterTestingModule,
      ],
      providers: [
        { provide: ProductService, useValue: productServiceMock },
        { provide: MatDialog, useValue: dialogMock },
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ProductList);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    fixture.destroy(); // Trigger ngOnDestroy to clean up subscriptions
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  it('should call getProducts on init and subscribe to products$', () => {
    productServiceMock.getProducts.and.callFake(() => {
      productsSubject.next(mockProducts);
    });

    fixture.detectChanges(); // ngOnInit

    expect(productServiceMock.getProducts).toHaveBeenCalled();
    expect(component.dataSource.data).toEqual(mockProducts);
  });

  describe('deleteProduct', () => {
    it('should open confirmation dialog', () => {
      dialogMock.open.and.returnValue({ afterClosed: () => of(false) } as any);
      component.deleteProduct(1);
      expect(dialogMock.open).toHaveBeenCalled();
    });

    it('should call productService.deleteProduct if dialog is confirmed', () => {
      dialogMock.open.and.returnValue({ afterClosed: () => of(true) } as any);
      productServiceMock.deleteProduct.and.returnValue(of({}));

      component.deleteProduct(1);

      expect(productServiceMock.deleteProduct).toHaveBeenCalledWith(1);
    });

    it('should NOT call productService.deleteProduct if dialog is dismissed', () => {
      dialogMock.open.and.returnValue({ afterClosed: () => of(false) } as any);

      component.deleteProduct(1);

      expect(productServiceMock.deleteProduct).not.toHaveBeenCalled();
    });
  });
});
