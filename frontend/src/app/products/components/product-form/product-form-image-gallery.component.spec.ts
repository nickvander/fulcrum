import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ProductFormImageGalleryComponent } from './product-form-image-gallery.component';
import { MatDialog } from '@angular/material/dialog';
import { of } from 'rxjs';
import { ProductImage } from '../../models/product.model';

describe('ProductFormImageGalleryComponent', () => {
  let component: ProductFormImageGalleryComponent;
  let fixture: ComponentFixture<ProductFormImageGalleryComponent>;
  let mockDialog: jasmine.SpyObj<MatDialog>;

  const mockImage: ProductImage = {
    id: 1,
    product_id: 1,
    image_path: 'test.jpg',
    is_primary: 0,
    title: 'Test Image',
    description: 'Test Description'
  };

  beforeEach(async () => {
    mockDialog = jasmine.createSpyObj('MatDialog', ['open']);

    await TestBed.configureTestingModule({
      imports: [ProductFormImageGalleryComponent],
      providers: [
        { provide: MatDialog, useValue: mockDialog },
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ProductFormImageGalleryComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should format image URL correctly', () => {
    const imagePath = 'test.jpg';
    const formattedUrl = component.getImageUrl(imagePath);
    expect(formattedUrl).toBe('/uploads/product_images/test.jpg');
  });

  it('should add staged images when onFileSelected is called', () => {
    const testFile = new File([], 'test.jpg');
    const event = {
      target: {
        files: [testFile]
      }
    } as unknown as Event;

    spyOn(URL, 'createObjectURL').and.returnValue('blob:test');
    spyOn(component.stagedImagesChange, 'emit');
    spyOn(component.stagedImagePreviewsChange, 'emit');

    component.onFileSelected(event);

    expect(component.stagedImagesChange.emit).toHaveBeenCalledWith([testFile]);
  });

  it('should remove staged image when removeStagedImage is called', () => {
    component.stagedImages = [new File([], 'test1.jpg'), new File([], 'test2.jpg')];
    component.stagedImagePreviews = ['preview1', 'preview2'];
    
    spyOn(component.stagedImagesChange, 'emit');
    spyOn(component.stagedImagePreviewsChange, 'emit');

    component.removeStagedImage(0);

    expect(component.stagedImagesChange.emit).toHaveBeenCalledWith([new File([], 'test2.jpg')]);
    expect(component.stagedImagePreviewsChange.emit).toHaveBeenCalledWith(['preview2']);
  });

  it('should open image dialog when openImageDialog is called', () => {
    const mockDialogRef = jasmine.createSpyObj('MatDialogRef', ['afterClosed']);
    mockDialogRef.afterClosed.and.returnValue(of(null));
    mockDialog.open.and.returnValue(mockDialogRef as any);

    component.productId = 1;
    component.openImageDialog(mockImage);

    expect(mockDialog.open).toHaveBeenCalledWith(
      jasmine.any(Function),
      jasmine.objectContaining({
        width: '500px',
        data: { image: mockImage, productId: 1 }
      })
    );
  });

  it('should emit event to delete image when deleteImage is called', () => {
    const event = new Event('click');
    spyOn(event, 'stopPropagation');
    const mockDialogRef = jasmine.createSpyObj('MatDialogRef', ['afterClosed']);
    mockDialogRef.afterClosed.and.returnValue(of(true));
    mockDialog.open.and.returnValue(mockDialogRef as any);
    spyOn(component.imagesToDelete, 'emit');

    component.deleteImage(event, 1);

    expect(event.stopPropagation).toHaveBeenCalled();
    expect(component.imagesToDelete.emit).toHaveBeenCalledWith([1]);
  });

  it('should emit primary image change when setPrimaryImage is called', () => {
    const event = new Event('click');
    spyOn(event, 'stopPropagation');
    spyOn(component.primaryImageChange, 'emit');

    component.setPrimaryImage(event, 1);

    expect(event.stopPropagation).toHaveBeenCalled();
    expect(component.primaryImageChange.emit).toHaveBeenCalledWith(1);
  });
});