import { Component, Inject, OnInit } from '@angular/core';

import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { ProductImage } from '../../../products/models/product.model';
import { ProductService } from '../../../products/services/product';
import { NotificationService } from '../../../core/services/notification.service';
import { TranslocoModule } from '@ngneat/transloco';

@Component({
  selector: 'app-image-dialog',
  standalone: true,
  imports: [TranslocoModule, 
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule
  ],
  templateUrl: './image-dialog.html',
  styleUrls: ['./image-dialog.scss']
})
export class ImageDialogComponent implements OnInit {
  imageForm: FormGroup;
  currentImage: ProductImage;

  constructor(
    public dialogRef: MatDialogRef<ImageDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { image: ProductImage, productId: number },
    private fb: FormBuilder,
    private productService: ProductService,
    private notificationService: NotificationService
  ) {
    this.currentImage = { ...data.image };
    this.imageForm = this.fb.group({
      title: [this.currentImage.title || '', Validators.maxLength(100)],
      description: [this.currentImage.description || '', Validators.maxLength(500)]
    });
  }

  ngOnInit(): void { }

  onNoClick(): void {
    this.dialogRef.close();
  }

  onSave(): void {
    if (this.imageForm.valid && this.data.productId) {
      const updatedData = {
        title: this.imageForm.value.title,
        description: this.imageForm.value.description
      };

      this.productService.updateProductImage(this.data.productId, this.currentImage.id, updatedData)
        .subscribe({
          next: (updatedImage) => {
            this.notificationService.showSuccess('Image details updated successfully');
            // Return the updated image to the calling component
            this.dialogRef.close(updatedImage);
          },
          error: (error) => {
            this.notificationService.showError('Failed to update image details');
            console.error('Error updating image:', error);
          }
        });
    }
  }

  getImageUrl(imagePath: string): string {
    if (imagePath && imagePath.startsWith('http')) return imagePath;
    return `/uploads/product_images/${imagePath}`;
  }
}