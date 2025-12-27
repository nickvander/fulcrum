import type { MockedObject } from "vitest";
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ProductFormImageGalleryComponent } from './product-form-image-gallery.component';
import { MatDialog } from '@angular/material/dialog';
import { of } from 'rxjs';
import { ProductImage } from '../../models/product.model';

describe('ProductFormImageGalleryComponent', () => {
    let component: ProductFormImageGalleryComponent;
    let fixture: ComponentFixture<ProductFormImageGalleryComponent>;
    let mockDialog: MockedObject<MatDialog>;

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
});
