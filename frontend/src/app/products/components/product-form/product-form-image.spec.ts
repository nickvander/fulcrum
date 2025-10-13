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
import { ImageDialogComponent } from '../../../shared/components/image-dialog/image-dialog';
import { ConfirmationDialog } from '../../../shared/components/confirmation-dialog/confirmation-dialog';

import { CustomFieldService } from '../../../settings/services/custom-field.service';
import { environment } from '../../../../environments/environment';

import { NotificationService } from '../../../core/services/notification.service';

describe('ProductForm: Image Management', () => {
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
  };

  beforeEach(async () => {
    productServiceMock = jasmine.createSpyObj('ProductService', ['createProduct', 'updateProduct', 'saveCustomFieldValues', 'updateProductImage', 'deleteProductImage', 'setPrimaryProductImage']);
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
        CustomFieldService,
        { provide: Router, useValue: routerMock },
        { provide: ActivatedRoute, useValue: activatedRouteMock }
      ]
    })
    .overrideComponent(ProductForm, {
      remove: { imports: [ImageDialogComponent, ConfirmationDialog] }
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

  it('should navigate to /products on cancel', () => {
    component.onCancel();
    expect(routerMock.navigate).toHaveBeenCalledWith(['/products']);
  });
  
  describe('image handling', () => {
    beforeEach(() => {
      // These tests require the component to be in "edit mode"
      activatedRouteMock.snapshot.params['id'] = mockProduct.id;
      routerMock.getCurrentNavigation.and.returnValue(null);
      fixture.detectChanges();
      const req = httpMock.expectOne(`${environment.apiUrl}/custom-fields`);
      req.flush([]);
    });

    it('should format image URL correctly', () => {
      const imagePath = 'test.jpg';
      const formattedUrl = component.getImageUrl(imagePath);
      expect(formattedUrl).toBe('/uploads/product_images/test.jpg');
    });

    it('should prevent default behavior and open confirmation dialog when deleteImage is called', () => {
      const event = new Event('click');
      spyOn(event, 'stopPropagation');
      const mockDialogRef = jasmine.createSpyObj('MatDialogRef', ['afterClosed']);
      mockDialogRef.afterClosed.and.returnValue(of(true)); // Simulate user confirming deletion
      dialogMock.open.and.returnValue(mockDialogRef as any);
      productServiceMock.deleteProductImage.and.returnValue(of(null));

      component.deleteImage(event, 1);

      expect(event.stopPropagation).toHaveBeenCalled();
      expect(dialogMock.open).toHaveBeenCalledWith(jasmine.any(Function), jasmine.objectContaining({
        data: {
          title: 'Delete Image?',
          message: 'Are you sure you want to delete this image? This action cannot be undone.'
        }
      }));
      expect(mockDialogRef.afterClosed).toHaveBeenCalled();
    });

    it('should prevent default behavior and call productService.setPrimaryProductImage when setPrimaryImage is called', () => {
      const event = new Event('click');
      spyOn(event, 'stopPropagation');
      productServiceMock.setPrimaryProductImage.and.returnValue(of(null));

      component.setPrimaryImage(event, 1);

      expect(event.stopPropagation).toHaveBeenCalled();
      expect(productServiceMock.setPrimaryProductImage).toHaveBeenCalledWith(1, 1);
    });
    
    it('should open image dialog when openImageDialog is called', () => {
      const mockImage = { id: 1, product_id: 1, image_path: 'test.jpg', is_primary: 1 };
      const mockDialogRef = jasmine.createSpyObj('MatDialogRef', ['afterClosed']);
      mockDialogRef.afterClosed.and.returnValue(of(null));
      dialogMock.open.and.returnValue(mockDialogRef as any);
      
      // Set productId for the component to test
      component.isEditMode = true;
      component.productId = 1;

      component.openImageDialog(mockImage);

      expect(dialogMock.open).toHaveBeenCalledWith(
        ImageDialogComponent,
        jasmine.objectContaining({
          width: '500px',
          data: { image: mockImage, productId: 1 }
        })
      );
    });
  });
});
