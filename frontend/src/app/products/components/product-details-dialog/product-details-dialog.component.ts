import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { Product } from '../../models/product.model';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { ProductService } from '../../services/product';

@Component({
    selector: 'app-product-details-dialog',
    templateUrl: './product-details-dialog.component.html',
    styleUrls: ['./product-details-dialog.component.scss'],
    standalone: true,
    imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule, MatDividerModule]
})
export class ProductDetailsDialogComponent {
    product!: Product;
    purchaseHistory: any[] = [];
    showHistory = false;

    constructor(
        public dialogRef: MatDialogRef<ProductDetailsDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: Product,
        private productService: ProductService,
        private router: Router
    ) {
        // Initialize with passed data for immediate display
        this.product = data;
        // Then fetch fresh data to ensure costs/inventory are up to date
        this.refreshProductData();
        this.loadHistory();
    }

    refreshProductData() {
        if (!this.product || !this.product.id) return;
        this.productService.getProductById(this.product.id).subscribe(freshProduct => {
            // Update the product object with fresh data
            this.product = freshProduct;
        });
    }

    onClose(): void {
        this.dialogRef.close();
    }

    loadHistory() {
        if (!this.product || !this.product.id) return;
        this.productService.getPurchaseHistory(this.product.id).subscribe(history => {
            this.purchaseHistory = history;
        });
    }

    async onGoToPO(poId: number): Promise<void> {
        console.log('Navigating to PO:', poId);
        // Try closing first, but ensure we don't block navigation
        this.dialogRef.close();

        try {
            // Correct path based on app-routing ('suppliers') and suppliers-routing ('po/:id')
            const result = await this.router.navigate(['/suppliers/po', poId]);
            console.log('Navigation result:', result);
        } catch (error) {
            console.error('Navigation error:', error);
        }
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
        if (path.startsWith('assets')) return path;

        // Normalize path: remove leading slash if present
        let cleanPath = path.startsWith('/') ? path.substring(1) : path;

        // If it's in uploads directory (checked by prefix)
        if (cleanPath.startsWith('uploads')) {
            return `/${cleanPath}`;
        }

        // If it has no other slashes, assume it's a product image filename
        if (!cleanPath.includes('/')) {
            return `/uploads/product_images/${cleanPath}`;
        }

        // Fallback: return original path (likely relative)
        return path;
    }
}
