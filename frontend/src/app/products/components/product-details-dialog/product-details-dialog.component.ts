import { Component, Inject, ViewChild, OnInit } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule, MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { Product } from '../../models/product.model';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { ProductService } from '../../services/product';
import { ProductForm } from '../product-form/product-form';
import { FormsModule } from '@angular/forms';
import { MatInputModule } from '@angular/material/input';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { CodeDisplayComponent } from '../../../shared/components/code-display/code-display.component';
import { MarketplaceListingDialogComponent, MarketplaceListingDialogData } from '../../../marketplaces/components/marketplace-listing-dialog/marketplace-listing-dialog.component';
import { NotificationService } from '../../../core/services/notification.service';
import { ImagePreviewDialogComponent } from './image-preview-dialog.component';

@Component({
    selector: 'app-product-details-dialog',
    templateUrl: './product-details-dialog.component.html',
    styleUrls: ['./product-details-dialog.component.scss'],
    standalone: true,
    imports: [
        CommonModule,
        MatDialogModule,
        MatButtonModule,
        MatIconModule,
        MatDividerModule,
        ProductForm,
        FormsModule,
        MatInputModule,
        MatInputModule,
        MatTooltipModule,
        TranslocoModule,
        CodeDisplayComponent
    ]
})
export class ProductDetailsDialogComponent implements OnInit {
    @ViewChild('productForm') productForm!: ProductForm;
    product!: Product;
    purchaseHistory: any[] = [];
    showHistory = false;
    isEditMode = false;
    isAssembling = false;
    assembleQuantity = 1;
    hasChanges = false;

    // New view state properties
    showFullDescription = false;
    showMarketplaces = false;
    showMarketing = false;
    showCodes = false; // Collapsed by default
    isMobile = false;
    isTablet = false;
    stagedImage: File | null = null;
    selectedImageIndex = 0;

    constructor(
        public dialogRef: MatDialogRef<ProductDetailsDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: { product: Product, mode?: 'view' | 'edit' | 'add', stagedImage?: File },
        private productService: ProductService,
        private router: Router,
        private dialog: MatDialog,
        private notificationService: NotificationService,
        private transloco: TranslocoService,
    ) {
        // Initialize with passed data for immediate display
        this.product = data.product;
        this.isEditMode = data.mode === 'edit' || data.mode === 'add';
        this.stagedImage = data.stagedImage || null;
    }

    get dialogTitle(): string {
        if (this.isEditMode) {
            const key = this.product.id
                ? (this.product.is_bundle ? 'products.dialogs.editBundle' : 'products.dialogs.editProduct')
                : (this.product.is_bundle ? 'products.dialogs.createBundle' : 'products.dialogs.addProduct');
            return this.transloco.translate(key);
        }
        return this.product.name;
    }

    ngOnInit(): void {
        this.refreshProductData();
        if (this.product?.id) {
            this.loadHistory(this.product.id);
        }
    }

    // Navigation stack for back functionality
    navigationStack: number[] = [];

    refreshProductData(id?: number) {
        const productId = id || this.product?.id;
        if (!productId) return;
        this.productService.getProductById(productId).subscribe(freshProduct => {
            // Update the product object with fresh data
            this.product = freshProduct;
        });
    }

    onNavigateToProduct(productId: number): void {
        if (this.product?.id && this.product.id !== productId) {
            this.navigationStack.push(this.product.id);
        }
        this.refreshProductData(productId);
        this.loadHistory(productId);
    }

    onNavigateBack(): void {
        const previousId = this.navigationStack.pop();
        if (previousId) {
            this.refreshProductData(previousId);
            this.loadHistory(previousId);
        }
    }

    onClose(): void {
        this.dialogRef.close();
    }

    loadHistory(productId: number): void {
        this.productService.getPurchaseHistory(productId).subscribe(history => {
            this.purchaseHistory = history;
        });
    }

    async onGoToPO(poId: number): Promise<void> {
        if (!poId) {
            console.error('Invalid PO ID:', poId);
            return;
        }
        await this.router.navigate(['/suppliers/po', poId]);
        this.onClose();
    }

    onEdit(): void {
        this.isEditMode = true;
    }

    onCancelEdit(): void {
        // If creating a new product (no ID), cancel means close the dialog
        if (!this.product.id) {
            this.dialogRef.close();
            return;
        }
        this.isEditMode = false;
    }

    onProductSaved(): void {
        this.isEditMode = false;
        this.hasChanges = true;
        this.refreshProductData();
    }

    saveProduct(): void {
        if (this.productForm) {
            this.productForm.onSubmit();
        }
    }

    get isFormInvalid(): boolean {
        return !this.productForm || !this.productForm.productForm || this.productForm.productForm.invalid;
    }

    getPrimaryImage(): string {
        if (!this.product || !this.product.images || this.product.images.length === 0) {
            return '';
        }
        const primary = this.product.images.find(img => img.is_primary == 1);
        return primary ? primary.image_path : this.product.images[0].image_path;
    }

    getActiveImage(): string {
        if (!this.product || !this.product.images || this.product.images.length === 0) {
            return '';
        }
        if (this.selectedImageIndex >= this.product.images.length) {
            this.selectedImageIndex = 0;
        }
        return this.product.images[this.selectedImageIndex].image_path;
    }

    selectImage(index: number): void {
        this.selectedImageIndex = index;
    }

    openImagePreview(): void {
        const imageUrl = this.getImageUrl(this.getActiveImage());
        if (!imageUrl) return;

        this.dialog.open(ImagePreviewDialogComponent, {
            data: { imageUrl },
            panelClass: 'image-preview-dialog-panel',
            maxWidth: '95vw',
            maxHeight: '95vh'
        });
    }

    getImageUrl(path: string): string {
        if (!path) return 'assets/placeholder.jpg';
        if (path.startsWith('http')) return path;
        // Match the path used in the rest of the app
        return `/uploads/product_images/${path}`;
    }

    getMarketplaceName(listing: any): string {
        if (!listing) return 'Marketplace';
        const url = listing.listing_url || '';
        if (url.includes('amazon')) return 'Amazon';
        if (url.includes('mercadolibre.com')) return 'MercadoLibre';
        
        // Fallback to IDs (assuming MercadoLibre was created first in this DB)
        switch (listing.marketplace_id) {
            case 1: return 'MercadoLibre';
            case 2: return 'Amazon';
            case 3: return 'Shopify';
            default: return 'Marketplace ' + listing.marketplace_id;
        }
    }

    getEffectiveCost(): number {
        // If it's a bundle and has 0 cost, try to estimate from components
        if (this.product.is_bundle && (!this.product.cost_price || this.product.cost_price === 0)) {
            if (this.product.bundle_components && this.product.bundle_components.length > 0) {
                return this.product.bundle_components.reduce((sum, bc) => {
                    const cost = bc.component_cost || 0;
                    return sum + (cost * bc.quantity);
                }, 0);
            }
        }
        return this.product.cost_price || 0;
    }

    getAllocatedStock(): number {
        if (!this.product.part_of_bundles) return 0;
        // This is tricky: we know which bundles it is part of, but do we know HOW MANY of those bundles are in stock?
        // The backend returns PartOfBundle[] which usually includes { bundle_stock: number, quantity: number }
        // So Allocated Stock = Sum(Bundle.Stock * Component.QuantityRequired)
        return this.product.part_of_bundles.reduce((sum, b) => {
            const bundleStock = b.bundle_stock || 0;
            const quantityRequired = b.quantity || 1;
            return sum + (bundleStock * quantityRequired);
        }, 0);
    }

    getAvailablePhysicalStock(): number {
        if (!this.product.inventory_items) return 0;
        return this.product.inventory_items.reduce((sum, item) => sum + item.quantity, 0);
    }

    getTotalPhysicalStock(): number {
        return this.getAvailablePhysicalStock() + this.getAllocatedStock();
    }

    // Matches product-list logic: Physical + Potential from Components
    getTotalStock(): number {
        // If it's a bundle, calculate how many we can make from components
        if (this.product.is_bundle) {
            let physicalStock = 0;
            if (this.product.inventory_items && this.product.inventory_items.length > 0) {
                const mainInventory = this.product.inventory_items.find(item => item.location === 'default');
                physicalStock = mainInventory ? mainInventory.quantity : this.product.inventory_items.reduce((acc, item) => acc + item.quantity, 0);
            }

            // Calculate potential from components
            if (this.product.bundle_components && this.product.bundle_components.length > 0) {
                const maxBundles = this.product.bundle_components.map(bc => {
                    const componentStock = bc.component_stock || 0;
                    const required = bc.quantity || 1;
                    return Math.floor(componentStock / required);
                });
                const virtualStock = Math.min(...maxBundles);
                return physicalStock + virtualStock;
            }
            return physicalStock;
        }

        return this.getAvailablePhysicalStock();
    }

    getPotentialStock(): number {
        if (!this.product.is_bundle || !this.product.bundle_components?.length) return 0;

        const maxBundles = this.product.bundle_components.map(bc => {
            const componentStock = bc.component_stock || 0;
            const required = bc.quantity || 1;
            return Math.floor(componentStock / required);
        });
        return Math.min(...maxBundles);
    }

    getMarketplaceLogo(listing: any): string | null {
        if (!listing) return null;
        const url = listing.listing_url || '';
        if (url.includes('amazon')) return 'assets/images/marketplaces/amazon.png';
        if (url.includes('mercadolibre.com')) return 'assets/images/marketplaces/mercadolibre.png';
        
        switch (listing.marketplace_id) {
            case 1: return 'assets/images/marketplaces/mercadolibre.png';
            case 2: return 'assets/images/marketplaces/amazon.png';
            default: return null;
        }
    }

    // Get unique marketplace listings (one per marketplace_id)
    getUniqueMarketplaceListings(): any[] {
        if (!this.product.marketplace_listings) return [];
        const seen = new Set<number>();
        return this.product.marketplace_listings.filter(listing => {
            if (seen.has(listing.marketplace_id)) {
                return false;
            }
            seen.add(listing.marketplace_id);
            return true;
        });
    }

    getBestMarketplacePromo(): any | null {
        if (!this.product.marketplace_listings || this.product.marketplace_listings.length === 0) {
            return null;
        }
        // Find the listing with the highest discount percentage
        return this.product.marketplace_listings
            .filter(l => l.original_price && l.original_price > l.marketplace_price)
            .sort((a, b) => (b.discount_percentage || 0) - (a.discount_percentage || 0))[0] || null;
    }

    startAssembly(): void {
        this.isAssembling = true;
        this.assembleQuantity = 1;
    }

    cancelAssembly(): void {
        this.isAssembling = false;
    }

    onCreateParentBundle(): void {
        this.dialogRef.close();
        const newBundle: Partial<Product> = {
            name: `Bundle including ${this.product.name}`,
            is_bundle: true,
            cost_price: this.product.cost_price,
            bundle_components: [{
                component_id: this.product.id!,
                component_name: this.product.name,
                component_image: this.getPrimaryImage(),
                quantity: 1
            } as any]
        };

        this.dialog.open(ProductDetailsDialogComponent, {
            data: {
                product: newBundle,
                mode: 'edit'
            },
            width: '1000px',
            maxWidth: '95vw',
            maxHeight: '90vh',
            panelClass: 'product-details-dialog-panel'
        });
    }

    confirmAssembly(): void {
        if (this.assembleQuantity <= 0) return;
        if (!this.product.id) return;

        this.productService.assembleBundle(this.product.id, this.assembleQuantity).subscribe({
            next: (updatedProduct: Product) => {
                this.product = updatedProduct;
                this.isAssembling = false;
            },
            error: (err: any) => console.error(err)
        });
    }

    onImageError(event: any): void {
        event.target.src = 'assets/placeholder.jpg';
    }

    navigateToQuickPost(postId: number): void {
        this.dialogRef.close();
        this.router.navigate(['/marketing'], { queryParams: { tab: 'quick-posts', highlight: postId } });
    }

    openListingDialog(marketplaceName: string = 'amazon'): void {
        if (!this.product?.id) return;

        const dialogRef = this.dialog.open(MarketplaceListingDialogComponent, {
            width: '600px',
            maxWidth: '95vw',
            data: {
                productId: this.product.id,
                productName: this.product.name,
                marketplace: marketplaceName,
                existingTitle: this.product.name,
                existingDescription: this.product.description
            } as MarketplaceListingDialogData
        });

        dialogRef.afterClosed().subscribe(result => {
            if (result) {
                // TODO: Handle saving the listing (call backend API)
                console.log('Listing data:', result);
                this.notificationService.showSuccess('Listing prepared! Publishing integration coming soon.');
            }
        });
    }
}
