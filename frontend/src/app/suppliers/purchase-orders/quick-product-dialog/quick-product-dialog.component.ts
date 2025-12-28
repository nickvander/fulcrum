import { Component, Inject, OnInit } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialog } from '@angular/material/dialog';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ProductService } from '../../../products/services/product';
import { Router } from '@angular/router';

@Component({
    selector: 'app-quick-product-dialog',
    templateUrl: './quick-product-dialog.component.html',
    styleUrls: ['./quick-product-dialog.component.scss'],
    standalone: false
})
export class QuickProductDialogComponent implements OnInit {
    productForm: FormGroup;
    isLoading = false;
    aiEnabled = false; // TODO: Check from AppSettings

    constructor(
        private fb: FormBuilder,
        private productService: ProductService,
        private router: Router,
        private dialog: MatDialog,
        public dialogRef: MatDialogRef<QuickProductDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: {
            suggestedName?: string;
            poFormState?: any;
            lineItemIndex?: number;
        }
    ) {
        this.productForm = this.fb.group({
            name: [data?.suggestedName || '', Validators.required],
            sku: [''],
            autoGenerateSku: [true],
            cost_price: [0, [Validators.required, Validators.min(0)]],
            default_resale_price: [0, [Validators.min(0)]]
        });
    }

    ngOnInit(): void {
        // Check if AI is enabled (from settings service in future)
        // For now, enable it to show the UI
        this.aiEnabled = true;

        // Disable SKU field when auto-generate is checked
        this.productForm.get('autoGenerateSku')?.valueChanges.subscribe(autoGen => {
            const skuControl = this.productForm.get('sku');
            if (autoGen) {
                skuControl?.disable();
                skuControl?.setValue('');
            } else {
                skuControl?.enable();
            }
        });

        // Trigger initial state
        if (this.productForm.get('autoGenerateSku')?.value) {
            this.productForm.get('sku')?.disable();
        }
    }

    onCancel(): void {
        this.dialogRef.close();
    }

    openCameraCapture(): void {
        // Import and open the camera capture dialog
        // For now, we'll use a simple approach - open the product ingestion in a dialog
        // This will be enhanced when the ProductIngestion component is made dialog-compatible

        // Placeholder: Show alert for now
        alert('Camera capture coming soon! This will use AI to identify products.');

        // Future implementation:
        // const dialogRef = this.dialog.open(CameraCaptureDialogComponent, {
        //   width: '600px',
        //   data: {}
        // });
        // dialogRef.afterClosed().subscribe(result => {
        //   if (result) {
        //     this.productForm.patchValue(result);
        //   }
        // });
    }

    createAndEditFull(): void {
        // Save current PO state before navigating
        // This allows the user to return to their work in progress
        const poState = this.data.poFormState;
        if (poState) {
            sessionStorage.setItem('draft_po_state', JSON.stringify(poState));
        }

        // Create the product first, then navigate to the full edit page
        if (this.productForm.get('name')?.value) {
            this.onSubmit(true); // Pass flag to navigate after creation
        } else {
            // Just close and navigate to new product page
            this.dialogRef.close({ action: 'navigateToProduct' });
            this.router.navigate(['/products/new'], {
                queryParams: { returnTo: 'po' }
            });
        }
    }

    onSubmit(navigateAfter: boolean = false): void {
        if (this.productForm.valid || (this.productForm.get('autoGenerateSku')?.value && this.productForm.get('name')?.valid)) {
            this.isLoading = true;

            const formValue = this.productForm.getRawValue();
            const productData: any = {
                name: formValue.name,
                cost_price: formValue.cost_price,
                default_resale_price: formValue.default_resale_price
            };

            // Only add SKU if not auto-generating and has value
            if (!formValue.autoGenerateSku && formValue.sku) {
                productData.sku = formValue.sku;
            }
            // If auto-generate is true, backend will generate the SKU

            this.productService.createProduct(productData).subscribe({
                next: (product) => {
                    this.isLoading = false;
                    if (navigateAfter) {
                        this.dialogRef.close();
                        this.router.navigate(['/products', product.id, 'edit']);
                    } else {
                        this.dialogRef.close(product);
                    }
                },
                error: (err) => {
                    this.isLoading = false;
                    console.error('Error creating product:', err);
                }
            });
        }
    }
}
