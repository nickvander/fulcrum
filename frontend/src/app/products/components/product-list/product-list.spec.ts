import { TestBed, ComponentFixture } from '@angular/core/testing';
import { ProductList } from './product-list';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { ProductService } from '../../services/product';
import { MatDialog } from '@angular/material/dialog';
import { of, BehaviorSubject } from 'rxjs';
import { Product } from '../../models/product.model';
import { PaginatedProducts } from '../../models/paginated-products.model';
import { Component } from '@angular/core';
import { SharedModule } from '../../../shared/shared-module';

// Create a stub for the AiSearchBar component
@Component({
  selector: 'app-ai-search-bar',
  template: '',
  standalone: true,
})
class AiSearchBarStubComponent {}

describe('ProductList', () => {
  let component: ProductList;
  let fixture: ComponentFixture<ProductList>;
  let productServiceMock: jasmine.SpyObj<ProductService>;
  let dialogMock: jasmine.SpyObj<MatDialog>;
  let productsSubject: BehaviorSubject<Product[]>;

  const mockProducts: Product[] = [
    { 
      id: 1, 
      name: 'Product 1', 
      sku: 'P001', 
      description: '', 
      default_resale_price: 10,
      images: [
        { id: 1, product_id: 1, image_path: 'product1.jpg', is_primary: 1 },
        { id: 2, product_id: 1, image_path: 'product1-alt.jpg', is_primary: 0 }
      ],
      primary_image: { id: 1, product_id: 1, image_path: 'product1.jpg', is_primary: 1 }
    },
    { 
      id: 2, 
      name: 'Product 2', 
      sku: 'P002', 
      description: '', 
      default_resale_price: 20,
      images: [
        { id: 3, product_id: 2, image_path: 'product2.jpg', is_primary: 1 }
      ],
      primary_image: { id: 3, product_id: 2, image_path: 'product2.jpg', is_primary: 1 }
    },
    { 
      id: 3, 
      name: 'Product 3', 
      sku: 'P003', 
      description: '', 
      default_resale_price: 30,
      images: [],
      primary_image: undefined
    },
  ];
  
  const mockPaginatedProducts: PaginatedProducts = {
    data: mockProducts,
    currentPage: 1,
    totalPages: 1,
    totalItems: 3,
    pageSize: 10,
    hasNextPage: false,
    hasPrevPage: false
  };

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
    })
    .overrideComponent(ProductList, {
      remove: { imports: [SharedModule] },
      add: { imports: [AiSearchBarStubComponent] }
    })
    .compileComponents();

    fixture = TestBed.createComponent(ProductList);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    fixture.destroy();
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  it('should call getProducts on init and subscribe to products$', () => {
    productServiceMock.getProducts.and.returnValue(of(mockPaginatedProducts));

    fixture.detectChanges(); // ngOnInit

    expect(productServiceMock.getProducts).toHaveBeenCalled();
    
    // The subscription to products$ will update the data
    productsSubject.next(mockProducts);
    expect(component.products).toEqual(mockProducts);
  });

  describe('deleteProduct', () => {
    it('should open confirmation dialog', () => {
      dialogMock.open.and.returnValue({ afterClosed: () => of(false) } as any);
      component.deleteProduct(1);
      expect(dialogMock.open).toHaveBeenCalled();
    });

    it('should call productService.deleteProduct if dialog is confirmed', () => {
      dialogMock.open.and.returnValue({ afterClosed: () => of(true) } as any);
      productServiceMock.deleteProduct.and.returnValue(of(null));

      component.deleteProduct(1);

      expect(productServiceMock.deleteProduct).toHaveBeenCalledWith(1);
    });

    it('should NOT call productService.deleteProduct if dialog is dismissed', () => {
      dialogMock.open.and.returnValue({ afterClosed: () => of(false) } as any);

      component.deleteProduct(1);

      expect(productServiceMock.deleteProduct).not.toHaveBeenCalled();
    });
  });
  
  describe('image handling', () => {
    beforeEach(() => {
      productServiceMock.getProducts.and.returnValue(of(mockPaginatedProducts));
      fixture.detectChanges(); // Initialize with mock products
    });
    
    it('should get primary image when primary image exists', () => {
      const productWithPrimary = mockProducts[0];
      const primaryImagePath = component.getPrimaryImage(productWithPrimary);
      expect(primaryImagePath).toBe('product1.jpg');
    });
    
    it('should get first image when no primary image exists', () => {
      const productWithoutPrimary = { ...mockProducts[0] };
      productWithoutPrimary.primary_image = undefined; // No primary image
      const imagePath = component.getPrimaryImage(productWithoutPrimary);
      expect(imagePath).toBe('product1.jpg'); // First image in the array
    });
    
    it('should return placeholder when no images exist', () => {
      const productWithoutImages = mockProducts[2]; // Product with no images
      const imagePath = component.getPrimaryImage(productWithoutImages);
      expect(imagePath).toBe('placeholder.jpg');
    });
    
    it('should format image URL correctly', () => {
      const imagePath = 'test.jpg';
      const formattedUrl = component.getImageUrl(imagePath);
      expect(formattedUrl).toBe('/uploads/product_images/test.jpg');
    });
    
    it('should handle image errors by setting placeholder', () => {
      const mockEvent = {
        target: { src: 'original.jpg' }
      };
      component.onImageError(mockEvent);
      expect(mockEvent.target.src).toContain('data:image');
    });
  });
  
  describe('loadProducts functionality', () => {
    it('should load products with pagination', () => {
      const mockPaginatedResponse: PaginatedProducts = {
        data: mockProducts,
        currentPage: 1,
        totalPages: 1,
        totalItems: 3,
        pageSize: 10,
        hasNextPage: false,
        hasPrevPage: false
      };
      
      productServiceMock.getProducts.and.returnValue(of(mockPaginatedResponse));
      component.loadProducts(1, 10);
      
      expect(productServiceMock.getProducts).toHaveBeenCalledWith(1, 10, undefined);
      expect(component.products).toEqual(mockProducts);
    });
  });
});