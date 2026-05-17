import type { MockedObject } from "vitest";
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { of, throwError } from 'rxjs';
import { ImageDialogComponent } from './image-dialog';
import { ProductImage } from '../../../products/models/product.model';
import { ProductService } from '../../../products/services/product';
import { NotificationService } from '../../../core/services/notification.service';
import { TranslocoTestingModule } from '@ngneat/transloco';

describe('ImageDialogComponent', () => {
    let component: ImageDialogComponent;
    let fixture: ComponentFixture<ImageDialogComponent>;
    let productServiceMock: MockedObject<ProductService>;
    let notificationServiceMock: MockedObject<NotificationService>;
    let mockDialogRef: MockedObject<MatDialogRef<ImageDialogComponent>>;

    const mockImage: ProductImage = {
        id: 1,
        product_id: 1,
        image_path: 'test-image.jpg',
        is_primary: 0,
        title: 'Test Image',
        description: 'Test description'
    };

    beforeEach(async () => {
        productServiceMock = {
            updateProductImage: vi.fn().mockName("ProductService.updateProductImage")
        } as any;
        notificationServiceMock = {
            showSuccess: vi.fn().mockName("NotificationService.showSuccess"),
            showError: vi.fn().mockName("NotificationService.showError")
        } as any;
        mockDialogRef = {
            close: vi.fn().mockName("MatDialogRef.close")
        } as any;

        await TestBed.configureTestingModule({
            imports: [
        TranslocoTestingModule.forRoot({ langs: { en: {}, 'es-MX': {} } }),
                ImageDialogComponent,
                ReactiveFormsModule,
                MatDialogModule,
                MatFormFieldModule,
                MatInputModule,
                MatButtonModule,
                MatIconModule,
                BrowserAnimationsModule,
                HttpClientTestingModule,
            ],
            providers: [
                { provide: MAT_DIALOG_DATA, useValue: { image: mockImage, productId: 1 } },
                { provide: MatDialogRef, useValue: mockDialogRef },
                { provide: ProductService, useValue: productServiceMock },
                { provide: NotificationService, useValue: notificationServiceMock },
            ]
        })
            .compileComponents();

        fixture = TestBed.createComponent(ImageDialogComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should initialize the form with image data', () => {
        expect(component.imageForm.value.title).toBe('Test Image');
        expect(component.imageForm.value.description).toBe('Test description');
    });

    it('should close the dialog when cancel is clicked', () => {
        component.onNoClick();
        expect(mockDialogRef.close).toHaveBeenCalled();
    });

    it('should format image URL correctly', () => {
        const imagePath = 'test.jpg';
        const url = component.getImageUrl(imagePath);
        expect(url).toBe('/uploads/product_images/test.jpg');
    });

    describe('save functionality', () => {
        beforeEach(() => {
            component.imageForm.controls['title'].setValue('Updated Title');
            component.imageForm.controls['description'].setValue('Updated Description');
        });

        it('should call updateProductImage when form is valid and save is clicked', () => {
            productServiceMock.updateProductImage.mockReturnValue(of({ ...mockImage, title: 'Updated Title', description: 'Updated Description' }));

            component.onSave();

            expect(productServiceMock.updateProductImage).toHaveBeenCalledWith(1, 1, { title: 'Updated Title', description: 'Updated Description' });
        });

        it('should show success notification and close dialog on successful save', () => {
            const updatedImage = { ...mockImage, title: 'Updated Title', description: 'Updated Description' } as any;
            productServiceMock.updateProductImage.mockReturnValue(of(updatedImage));

            component.onSave();

            expect(notificationServiceMock.showSuccess).toHaveBeenCalledWith('Image details updated successfully');
            expect(mockDialogRef.close).toHaveBeenCalledWith(updatedImage);
        });

        it('should show error notification when saving fails', () => {
            const errorResponse = 'Error occurred';
            productServiceMock.updateProductImage.mockReturnValue(throwError(() => errorResponse));

            component.onSave();

            expect(notificationServiceMock.showError).toHaveBeenCalledWith('Failed to update image details');
        });

        it('should not call updateProductImage when form is invalid', () => {
            component.imageForm.controls['title'].setValue('A'.repeat(101)); // Exceeds max length

            component.onSave();

            expect(productServiceMock.updateProductImage).not.toHaveBeenCalled();
        });
    });
});
