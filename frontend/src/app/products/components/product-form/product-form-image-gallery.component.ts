import { Component, Input, Output, EventEmitter, OnInit, ViewChild, ElementRef } from '@angular/core';

import { ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog } from '@angular/material/dialog';
import { CdkDrag, CdkDragHandle, CdkDropList } from '@angular/cdk/drag-drop';
import { ProductImage } from '../../models/product.model';
import { ImageDialogComponent } from '../../../shared/components/image-dialog/image-dialog';
import { ConfirmationDialog } from '../../../shared/components/confirmation-dialog/confirmation-dialog';
import { ProductService } from '../../services/product';

@Component({
  selector: 'app-product-form-image-gallery',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatIconModule,
    MatListModule,
    MatTooltipModule,
    CdkDropList,
    CdkDrag,
    CdkDragHandle
  ],
  templateUrl: './product-form-image-gallery.component.html',
  styleUrls: ['./product-form-image-gallery.component.scss']
})
export class ProductFormImageGalleryComponent implements OnInit {
  @Input() existingImages: ProductImage[] = [];
  @Input() stagedImages: File[] = [];
  @Input() stagedImagePreviews: string[] = [];
  @Input() productId: number | null = null;
  @Output() stagedImagesChange = new EventEmitter<File[]>();
  @Output() stagedImagePreviewsChange = new EventEmitter<string[]>();
  @Output() imagesToDelete = new EventEmitter<number[]>();
  @Output() primaryImageChange = new EventEmitter<number | null>();
  @Output() imageUpdated = new EventEmitter<{ imageId: number, field: 'title' | 'description', value: string }>();
  @Output() existingImagesChange = new EventEmitter<ProductImage[]>();

  @ViewChild('fileInput', { static: false }) fileInput!: ElementRef<HTMLInputElement>;

  constructor(
    private dialog: MatDialog,
    private productService: ProductService
  ) { }

  ngOnInit(): void { }

  getImageUrl(imagePath: string): string {
    if (imagePath.startsWith('http')) return imagePath;

    return `/uploads/product_images/${imagePath}`;
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) {
      const newStagedImages: File[] = [...this.stagedImages];
      const newStagedImagePreviews: string[] = [...this.stagedImagePreviews];

      Array.from(input.files).forEach(file => {
        newStagedImages.push(file);
        const reader = new FileReader();
        reader.onload = (e) => {
          if (e.target?.result) {
            newStagedImagePreviews.push(e.target.result as string);
            this.stagedImagePreviewsChange.emit(newStagedImagePreviews);
          }
        };
        reader.readAsDataURL(file);
      });

      this.stagedImagesChange.emit(newStagedImages);

      // Clear the input value to allow selecting the same file again
      input.value = '';
    }
  }

  removeStagedImage(index: number): void {
    const newStagedImages = [...this.stagedImages];
    const newStagedImagePreviews = [...this.stagedImagePreviews];

    newStagedImages.splice(index, 1);
    newStagedImagePreviews.splice(index, 1);

    this.stagedImagesChange.emit(newStagedImages);
    this.stagedImagePreviewsChange.emit(newStagedImagePreviews);
  }

  openImageDialog(image: ProductImage): void {
    if (!this.productId) return;

    const dialogRef = this.dialog.open(ImageDialogComponent, {
      width: '500px',
      data: { image: image, productId: this.productId }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        // Emit event to parent component to update image details
        this.imageUpdated.emit({
          imageId: result.id,
          field: 'title',
          value: result.title
        });
        this.imageUpdated.emit({
          imageId: result.id,
          field: 'description',
          value: result.description
        });
      }
    });
  }

  deleteImage(event: Event, imageId: number): void {
    event.stopPropagation(); // Prevent opening the dialog when deleting

    const dialogRef = this.dialog.open(ConfirmationDialog, {
      data: {
        title: 'Delete Image?',
        message: 'Are you sure you want to delete this image? This will be permanent once you save.'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.imagesToDelete.emit([imageId]);
      }
    });
  }

  setPrimaryImage(event: Event, imageId: number): void {
    event.stopPropagation(); // Prevent opening the dialog when setting primary
    this.primaryImageChange.emit(imageId);
  }

  onImageReorder(event: any): void {
    const prevIndex = this.existingImages.findIndex(img => img.id === event.item.data.id);
    const imageToMove = this.existingImages[prevIndex];

    // Remove from old position and insert at new position
    const newImagesList = [...this.existingImages];
    newImagesList.splice(prevIndex, 1);
    newImagesList.splice(event.currentIndex, 0, imageToMove);

    // Emit the reordered list to update parent view immediately (Optimistic UI)
    this.existingImagesChange.emit(newImagesList);

    // If we are in edit mode (have a product ID), persist the order immediately
    if (this.productId) {
      const newOrderIds = newImagesList.map(img => img.id);
      this.productService.updateImageOrder(this.productId, newOrderIds).subscribe({
        next: () => {
          console.log('Image order updated successfully');
        },
        error: (err) => {
          console.error('Failed to update image order', err);
          // Revert the list on error?
          // For now, we accept the optimistic UI might be out of sync until refresh
          // or we could re-emit the original list here.
          this.existingImagesChange.emit(this.existingImages); // Revert
        }
      });
    }
  }

  trackByFn(index: number, item: ProductImage): any {
    return item.id;
  }
}