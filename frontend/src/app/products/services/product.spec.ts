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
    { id: 1, name: 'Product 1', sku: 'P001', description: '', default_resale_price: 10 },
    { id: 2, name: 'Product 2', sku: 'P002', description: '', default_resale_price: 20 },
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
      service.getProducts();

      const req = httpMock.expectOne(`${environment.apiUrl}/products`);
      expect(req.request.method).toBe('GET');
      req.flush(mockProducts);

      service.products$.subscribe(products => {
        expect(products).toEqual(mockProducts);
      });
    });
  });

  describe('createProduct', () => {
    it('should create a product, update the stream, and show notification', () => {
      const newProduct: Omit<Product, 'id'> = { name: 'New Product', sku: 'P003', description: '', default_resale_price: 30 };
      const createdProduct: Product = { id: 3, ...newProduct };

      service.createProduct(newProduct).subscribe(product => {
        expect(product).toEqual(createdProduct);
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/products`);
      expect(req.request.method).toBe('POST');
      req.flush(createdProduct);

      service.products$.subscribe(products => {
        expect(products.length).toBe(1);
        expect(products[0]).toEqual(createdProduct);
      });

      expect(notificationServiceMock.showSuccess).toHaveBeenCalledWith('Product created successfully!');
    });
  });

  describe('updateProduct', () => {
    it('should update a product, update the stream, and show notification', () => {
      service.getProducts();
      const getReq = httpMock.expectOne(`${environment.apiUrl}/products`);
      getReq.flush(mockProducts);

      const updatedProduct: Product = { ...mockProducts[0], name: 'Updated Name' };

      service.updateProduct(updatedProduct).subscribe(product => {
        expect(product).toEqual(updatedProduct);
      });

      const putReq = httpMock.expectOne(`${environment.apiUrl}/products/${updatedProduct.id}`);
      expect(putReq.request.method).toBe('PUT');
      putReq.flush(updatedProduct);

      service.products$.subscribe(products => {
        expect(products.length).toBe(2);
        expect(products[0].name).toBe('Updated Name');
      });

      expect(notificationServiceMock.showSuccess).toHaveBeenCalledWith('Product updated successfully!');
    });
  });

  describe('deleteProduct', () => {
    it('should delete a product, update the stream, and show notification', () => {
      service.getProducts();
      const getReq = httpMock.expectOne(`${environment.apiUrl}/products`);
      getReq.flush(mockProducts);

      const productIdToDelete = 1;
      service.deleteProduct(productIdToDelete).subscribe();

      const deleteReq = httpMock.expectOne(`${environment.apiUrl}/products/${productIdToDelete}`);
      expect(deleteReq.request.method).toBe('DELETE');
      deleteReq.flush({});

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

      const req = httpMock.expectOne(`${environment.apiUrl}/uploads`);
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
});
