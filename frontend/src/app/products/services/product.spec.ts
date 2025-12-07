import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { ProductService } from './product';
import { NotificationService } from '../../core/services/notification.service';
import { Product } from '../models/product.model';
import { environment } from '../../../environments/environment';

describe('ProductService', () => {
  let service: ProductService;
  let httpMock: HttpTestingController;
  let notificationServiceMock: jasmine.SpyObj<NotificationService>;

  const mockProducts: Product[] = [
    { id: 1, name: 'Product 1', sku: 'P001', description: '', default_resale_price: 10, images: [{ id: 1, product_id: 1, image_path: 'path/to/image1.jpg', is_primary: 1 }] },
    { id: 2, name: 'Product 2', sku: 'P002', description: '', default_resale_price: 20, images: [] },
  ];

  beforeEach(() => {
    const notificationSpy = jasmine.createSpyObj('NotificationService', ['showSuccess']);

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        ProductService,
        { provide: NotificationService, useValue: notificationSpy },
      ],
    });

    service = TestBed.inject(ProductService);
    httpMock = TestBed.inject(HttpTestingController);
    notificationServiceMock = TestBed.inject(NotificationService) as jasmine.SpyObj<NotificationService>;
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('getProducts', () => {
    it('should fetch products and update the products$ stream', () => {
      service.getProducts(1, 10).subscribe(); // Explicitly call with page and limit params

      const req = httpMock.expectOne(`${environment.apiUrl}/products?skip=0&limit=10`);
      expect(req.request.method).toBe('GET');
      req.flush({ data: mockProducts, currentPage: 1, totalPages: 1, totalItems: 2, pageSize: 10, hasNextPage: false, hasPrevPage: false });

      service.products$.subscribe(products => {
        expect(products[0].primary_image).toEqual(mockProducts[0].images![0]);
        expect(products[1].primary_image).toBeUndefined();
      });
    });
  });

  describe('createProduct', () => {
    it('should create a product, update the stream, and show notification', () => {
      const newProduct: Omit<Product, 'id'> = { name: 'New Product', sku: 'P003', description: '', default_resale_price: 30 };
      const createdProduct: Product = { id: 3, ...newProduct, images: [] };

      // Subscribe to the createProduct observable but don't expect anything immediately
      service.createProduct(newProduct).subscribe(product => {
        expect(product).toEqual(createdProduct);
      });

      // Expect and flush the POST request
      const req = httpMock.expectOne(`${environment.apiUrl}/products/`);
      expect(req.request.method).toBe('POST');
      req.flush(createdProduct);

      // Expect and flush the GET request that should be made after the POST
      const getReq = httpMock.expectOne(`${environment.apiUrl}/products?skip=0&limit=10`);
      getReq.flush([...mockProducts, createdProduct]);

      // Verify that the products stream was updated
      service.products$.subscribe(products => {
        expect(products.length).toBe(3);
        expect(products[2].primary_image).toBeUndefined();
      });

      // Verify that the notification was shown
      expect(notificationServiceMock.showSuccess).toHaveBeenCalledWith('Product created successfully!');
    });
  });

  describe('updateProduct', () => {
    it('should update a product, update the stream, and show notification', () => {
      // First populate the internal cache by calling getProducts
      service['getProductsLegacy']().subscribe();
      const req = httpMock.expectOne(`${environment.apiUrl}/products`);
      req.flush(mockProducts);

      const updatedProduct: Product = { ...mockProducts[0], name: 'Updated Name' };

      service.updateProduct(updatedProduct).subscribe(product => {
        expect(product).toEqual(updatedProduct);
      });

      const putReq = httpMock.expectOne(`${environment.apiUrl}/products/${updatedProduct.id}`);
      expect(putReq.request.method).toBe('PUT');
      expect(putReq.request.body).toEqual(updatedProduct);
      putReq.flush(updatedProduct);

      // Check if the BehaviorSubject has been updated correctly
      const currentProducts = service['_products'].getValue();
      expect(currentProducts.length).toBe(2);
      const updatedProductInCache = currentProducts.find(p => p.id === updatedProduct.id);
      expect(updatedProductInCache).toBeDefined();
      expect(updatedProductInCache?.name).toBe('Updated Name');

      expect(notificationServiceMock.showSuccess).toHaveBeenCalledWith('Product updated successfully!');
    });
  });

  describe('deleteProduct', () => {
    it('should delete a product, update the stream, and show notification', () => {
      const productIdToDelete = 1;
      service.deleteProduct(productIdToDelete).subscribe();

      const deleteReq = httpMock.expectOne(`${environment.apiUrl}/products/${productIdToDelete}`);
      expect(deleteReq.request.method).toBe('DELETE');
      deleteReq.flush({});

      const getReq = httpMock.expectOne(`${environment.apiUrl}/products?skip=0&limit=10`);
      getReq.flush(mockProducts.filter(p => p.id !== productIdToDelete));

      service.products$.subscribe(products => {
        expect(products.length).toBe(1);
        expect(products.find(p => p.id === productIdToDelete)).toBeUndefined();
      });

      expect(notificationServiceMock.showSuccess).toHaveBeenCalledWith('Product deleted successfully!');
    });
  });

  describe('uploadImage', () => {
    it('should upload an image and return the file path', () => {
      const dummyFile = new File([''], 'test.jpg');
      const mockResponse = { file_path: 'uploads/test.jpg' };

      service.uploadImage(dummyFile).subscribe(response => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/uploads/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body.get('file')).toEqual(dummyFile);
      req.flush(mockResponse);
    });
  });

  describe('identifyProductFromImage', () => {
    it('should send image path for identification', () => {
      const filePath = 'uploads/test.jpg';
      const mockResponse: Partial<Product> = { name: 'AI Product' };

      service.identifyProductFromImage(filePath).subscribe(response => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/ai/identify-from-image`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ image_path: filePath });
      req.flush(mockResponse);
    });
  });

  describe('uploadProductImage', () => {
    it('should upload a product-specific image', () => {
      const dummyFile = new File([''], 'product.jpg');
      const productId = 1;

      service.uploadProductImage(productId, dummyFile).subscribe();

      const req = httpMock.expectOne(`${environment.apiUrl}/products/${productId}/images`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body.get('file')).toEqual(dummyFile);
      req.flush({});
    });
  });

  describe('deleteMultipleProducts', () => {
    it('should delete multiple products and show notification', () => {
      const productIds = [1, 2, 3];

      service.deleteMultipleProducts(productIds).subscribe();

      const req = httpMock.expectOne(`${environment.apiUrl}/products/`);
      expect(req.request.method).toBe('DELETE');
      expect(req.request.body).toEqual({ ids: productIds });
      req.flush({ message: 'Successfully deleted 3 products', deleted_count: 3 });

      expect(notificationServiceMock.showSuccess).toHaveBeenCalledWith('Selected products deleted successfully!');
    });
  });
});
