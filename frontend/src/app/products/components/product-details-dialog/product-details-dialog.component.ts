import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { Product } from '../../models/product.model';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';

@Component({
    selector: 'app-product-details-dialog',
    templateUrl: './product-details-dialog.component.html',
    styleUrls: ['./product-details-dialog.component.scss'],
    standalone: true,
    imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule, MatDividerModule]
})
export class ProductDetailsDialogComponent {

    constructor(
        public dialogRef: MatDialogRef<ProductDetailsDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public product: Product
    ) { }

    onClose(): void {
        this.dialogRef.close();
    }

    onEdit(): void {
        this.dialogRef.close('edit');
    }

    getPrimaryImage(): string {
        if (this.product.images && this.product.images.length > 0) {
            const primary = this.product.images.find(img => img.is_primary);
            return primary ? primary.image_path : this.product.images[0].image_path;
        }
        return '';
    }

    getImageUrl(path: string | undefined): string {
        if (!path) return 'assets/placeholder.jpg';
        if (path.startsWith('http')) return path;
        // Assuming relative path from backend
        // In real app, this should be a service method (like imageService.getUrl(path))
        // Hardcoding for now based on known backend path structure or just returning path if it's full
        return path.includes('uploads') ? `http://localhost:8000/${path}` : path;
    }
}
