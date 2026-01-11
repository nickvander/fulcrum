import type { MockedObject } from "vitest";
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ProductFormImageGalleryComponent } from './product-form-image-gallery.component';
import { MatDialog } from '@angular/material/dialog';
import { of } from 'rxjs';
import { ProductImage } from '../../models/product.model';
import { ProductService } from '../../services/product';

describe('ProductFormImageGalleryComponent', () => {
    let component: ProductFormImageGalleryComponent;
    let fixture: ComponentFixture<ProductFormImageGalleryComponent>;
    let mockDialog: MockedObject<MatDialog>;
    let mockProductService: MockedObject<ProductService>;

    // Mock FileReader
    class MockFileReader {
        onload: any;
        onerror: any;
        readAsDataURL() {
            if (this.onload) {
                this.onload({ target: { result: 'data:image/png;base64,mock' } });
            }
        }
    }
    (window as any).FileReader = MockFileReader;

    const mockImage: ProductImage = {
        id: 1,
        product_id: 1,
        image_path: 'test.jpg',
        is_primary: 0,
        title: 'Test Image',
        description: 'Test Description'
    };

    beforeEach(async () => {
        mockDialog = {
            open: vi.fn().mockName("MatDialog.open")
        } as any;

        mockProductService = {
            updateImageOrder: vi.fn().mockReturnValue(of({}))
        } as any;

        await TestBed.configureTestingModule({
            imports: [ProductFormImageGalleryComponent],
            providers: [
                { provide: MatDialog, useValue: mockDialog },
                { provide: ProductService, useValue: mockProductService },
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

        vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test');
        vi.spyOn(component.stagedImagesChange, 'emit');
        vi.spyOn(component.stagedImagePreviewsChange, 'emit');

        component.onFileSelected(event);

        expect(component.stagedImagesChange.emit).toHaveBeenCalledWith([testFile]);
    });

    it('should remove staged image when removeStagedImage is called', () => {
        const file1 = new File([], 'test1.jpg');
        const file2 = new File([], 'test2.jpg');
        component.stagedImages = [file1, file2];
        component.stagedImagePreviews = ['preview1', 'preview2'];

        vi.spyOn(component.stagedImagesChange, 'emit');
        vi.spyOn(component.stagedImagePreviewsChange, 'emit');

        component.removeStagedImage(0);

        expect(component.stagedImagesChange.emit).toHaveBeenCalledWith([file2]);
        expect(component.stagedImagePreviewsChange.emit).toHaveBeenCalledWith(['preview2']);
    });

    it('should open image dialog when openImageDialog is called', () => {
        const mockDialogRef = {
            afterClosed: vi.fn().mockName("MatDialogRef.afterClosed")
        } as any;
        mockDialogRef.afterClosed.mockReturnValue(of(null));
        mockDialog.open.mockReturnValue(mockDialogRef as any);

        component.productId = 1;
        component.openImageDialog(mockImage);

        expect(mockDialog.open).toHaveBeenCalledWith(expect.any(Function), expect.objectContaining({
            width: '500px',
            data: { image: mockImage, productId: 1 }
        }));
    });

    it('should emit event to delete image when deleteImage is called', () => {
        const event = new Event('click');
        vi.spyOn(event, 'stopPropagation');
        const mockDialogRef = {
            afterClosed: vi.fn().mockName("MatDialogRef.afterClosed")
        } as any;
        mockDialogRef.afterClosed.mockReturnValue(of(true));
        mockDialog.open.mockReturnValue(mockDialogRef as any);
        vi.spyOn(component.imagesToDelete, 'emit');

        component.deleteImage(event, 1);

        expect(event.stopPropagation).toHaveBeenCalled();
        expect(component.imagesToDelete.emit).toHaveBeenCalledWith([1]);
    });

    it('should emit primary image change when setPrimaryImage is called', () => {
        const event = new Event('click');
        vi.spyOn(event, 'stopPropagation');
        vi.spyOn(component.primaryImageChange, 'emit');

        component.setPrimaryImage(event, 1);

        expect(event.stopPropagation).toHaveBeenCalled();
        expect(component.primaryImageChange.emit).toHaveBeenCalledWith(1);
    });

    it('should reorder images and call backend when onImageReorder is called with productId', () => {
        const image1 = { ...mockImage, id: 1 };
        const image2 = { ...mockImage, id: 2 };
        component.existingImages = [image1, image2];
        component.productId = 123;

        mockProductService.updateImageOrder.mockReturnValue(of({}));
        vi.spyOn(component.existingImagesChange, 'emit');

        // Mock Drop Event: moving index 1 (image2) to index 0
        const event = {
            item: { data: image2 },
            currentIndex: 0
        };

        component.onImageReorder(event);

        // Expected order: [image2, image1]
        expect(component.existingImagesChange.emit).toHaveBeenCalledWith([image2, image1]);

        const newOrderIds = [2, 1];
        expect(mockProductService.updateImageOrder).toHaveBeenCalledWith(123, newOrderIds);
    });

    it('should reorder images but NOT call backend when onImageReorder is called without productId', () => {
        const image1 = { ...mockImage, id: 1 };
        const image2 = { ...mockImage, id: 2 };
        component.existingImages = [image1, image2];
        component.productId = null; // No ID

        vi.spyOn(component.existingImagesChange, 'emit');

        const event = {
            item: { data: image2 },
            currentIndex: 0
        };

        component.onImageReorder(event);

        expect(component.existingImagesChange.emit).toHaveBeenCalledWith([image2, image1]);
        expect(mockProductService.updateImageOrder).not.toHaveBeenCalled();
    });
});
