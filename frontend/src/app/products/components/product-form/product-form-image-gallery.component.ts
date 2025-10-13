import { Component, Input, Output, EventEmitter, OnInit, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog } from '@angular/material/dialog';
import { ProductImage } from '../../models/product.model';
import { ImageDialogComponent } from '../../../shared/components/image-dialog/image-dialog';
import { ConfirmationDialog } from '../../../shared/components/confirmation-dialog/confirmation-dialog';

@Component({
  selector: 'app-product-form-image-gallery',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatIconModule,
    MatListModule,
    MatTooltipModule,
  ],
  template: `
    <div class="image-section">
      <div class="image-upload">
        <input hidden #fileInput type="file" (change)="onFileSelected($event)" accept="image/*" multiple>
        <button type="button" mat-stroked-button (click)="fileInput.click()">
          <mat-icon>add_a_photo</mat-icon>
          <span>Upload Image</span>
        </button>
      </div>

      <div class="staged-images" *ngIf="stagedImagePreviews.length > 0">
        <p class="mat-body-strong">New Images (to be uploaded on save):</p>
        <div class="image-gallery">
          <div *ngFor="let preview of stagedImagePreviews; let i = index" class="image-container">
            <img [src]="preview" alt="Staged image preview">
            <div class="image-overlay">
               <div class="image-overlay-content">
                  <button mat-icon-button class="overlay-button" color="warn" matTooltip="Remove" (click)="removeStagedImage(i)">
                    <mat-icon>close</mat-icon>
                  </button>
               </div>
            </div>
          </div>
        </div>
      </div>

      <mat-divider *ngIf="stagedImages.length > 0 && existingImages?.length"></mat-divider>
      
      <p class="mat-body-strong" *ngIf="existingImages?.length">Current Images:</p>
      <div class="image-gallery" *ngIf="existingImages?.length">
        <div *ngFor="let image of existingImages" class="image-container" [class.primary-image-container]="image.is_primary">
          <img [src]="getImageUrl(image.image_path)" [alt]="image.title || 'Product Image'" [class.primary-image]="image.is_primary" (click)="openImageDialog(image)">
          <div class="image-overlay" (click)="openImageDialog(image)">
            <div class="image-overlay-content">
              <button type="button" mat-icon-button class="overlay-button" matTooltip="Set as primary image" [class.selected]="image.is_primary" (click)="$event.stopPropagation(); setPrimaryImage($event, image.id)">
                <mat-icon>{{ image.is_primary ? 'star' : 'star_border' }}</mat-icon>
              </button>
              <button type="button" mat-icon-button class="overlay-button" color="warn" matTooltip="Delete image" (click)="$event.stopPropagation(); deleteImage($event, image.id)">
                <mat-icon>delete</mat-icon>
              </button>
            </div>
          </div>
        </div>
      </div>
      <div *ngIf="!existingImages?.length" class="no-images">
        <p *ngIf="!stagedImages.length">No images uploaded for this product yet.</p>
        <p *ngIf="stagedImages.length && !existingImages.length">No existing images. New images will be uploaded on save.</p>
      </div>
    </div>
  `,
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
  @Output() imageUpdated = new EventEmitter<{imageId: number, field: 'title' | 'description', value: string}>();

  @ViewChild('fileInput', { static: false }) fileInput!: ElementRef<HTMLInputElement>;

  constructor(private dialog: MatDialog) {}

  ngOnInit(): void {}

  getImageUrl(imagePath: string): string {
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
}