import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-image-preview-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule],
  template: `
    <div class="preview-container">
      <div class="header">
        <button mat-icon-button (click)="dialogRef.close()" class="close-btn">
          <mat-icon>close</mat-icon>
        </button>
      </div>
      <div class="image-wrapper">
        <img [src]="data.imageUrl" alt="Product Preview" (error)="onImageError($event)">
      </div>
    </div>
  `,
  styles: [`
    .preview-container {
      display: flex;
      flex-direction: column;
      background: #000;
      max-width: 95vw;
      max-height: 95vh;
      position: relative;
      overflow: hidden;
      border-radius: 8px;
    }
    .header {
      position: absolute;
      top: 8px;
      right: 8px;
      z-index: 10;
    }
    .close-btn {
      background: rgba(0, 0, 0, 0.5);
      color: white;
      &:hover {
        background: rgba(0, 0, 0, 0.8);
      }
    }
    .image-wrapper {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      height: 100%;
      min-height: 200px;
      img {
        max-width: 100%;
        max-height: 85vh;
        object-fit: contain;
        display: block;
      }
    }
  `]
})
export class ImagePreviewDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<ImagePreviewDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { imageUrl: string }
  ) {}

  onImageError(event: any): void {
    event.target.src = 'assets/placeholder.jpg';
  }
}
