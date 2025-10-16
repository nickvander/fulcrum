import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CdkDrag, CdkDragHandle, CdkDropList } from '@angular/cdk/drag-drop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

export interface ProductImage {
  id: number;
  image_path: string;
  is_primary: number;
  title?: string;
  description?: string;
}

@Component({
  selector: 'app-enhanced-image-management',
  standalone: true,
  imports: [
    CommonModule,
    CdkDropList,
    CdkDrag,
    CdkDragHandle,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule
  ],
  templateUrl: './enhanced-image-management.html',
  styleUrls: ['./enhanced-image-management.scss']
})
export class EnhancedImageManagementComponent {
  @Input() images: ProductImage[] = [];
  @Output() imageOrderChanged = new EventEmitter<ProductImage[]>();
  @Output() primaryImageChanged = new EventEmitter<number>();
  @Output() imageDeleted = new EventEmitter<number>();
  @Output() imageUpdated = new EventEmitter<{imageId: number, updates: Partial<ProductImage>}>();;
  @Output() altTextChanged = new EventEmitter<{imageId: number, altText: string}>();

  onReorder(event: any): void {
    // event.currentIndex and event.previousIndex will give us the old and new positions
    const prevIndex = this.images.findIndex(img => img.id === event.item.data.id);
    const imageToMove = this.images[prevIndex];
    
    // Remove from old position and insert at new position
    this.images.splice(prevIndex, 1);
    this.images.splice(event.currentIndex, 0, imageToMove);
    
    this.imageOrderChanged.emit(this.images);
  }

  setAsPrimary(imageId: number): void {
    // Update local array
    this.images.forEach(img => {
      img.is_primary = img.id === imageId ? 1 : 0;
    });
    this.primaryImageChanged.emit(imageId);
  }

  deleteImage(imageId: number): void {
    this.imageDeleted.emit(imageId);
  }

  updateImage(imageId: number, field: keyof ProductImage, value: any): void {
    this.imageUpdated.emit({ imageId, updates: { [field]: value } as Partial<ProductImage> });
  }

  onAltTextChange(imageId: number, altText: string): void {
    this.altTextChanged.emit({ imageId, altText });
  }

  getImageUrl(imagePath: string): string {
    // Backend serves images from the 'uploads/product_images' directory.
    return `/uploads/product_images/${imagePath}`;
  }

  onImageError(event: any): void {
    // Set a placeholder image if the image fails to load
    event.target.src = '/uploads/product_images/placeholder.jpg';
  }

  trackByFn(index: number, item: ProductImage): any {
    return item.id;
  }
}