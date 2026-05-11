import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { FormBuilder, FormGroup, FormArray, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { PurchaseOrder, PurchaseOrderItem } from '../../../shared/models/purchase-order.model';
import { SuppliersService } from '../../suppliers.service';

@Component({
    selector: 'app-receiving-dialog',
    templateUrl: './receiving-dialog.component.html',
    styleUrls: ['./receiving-dialog.component.scss'],
    standalone: true,
    imports: [
        CommonModule,
        ReactiveFormsModule,
        MatDialogModule,
        MatButtonModule,
        MatFormFieldModule,
        MatInputModule,
        MatIconModule,
        MatDividerModule
    ]
})
export class ReceivingDialogComponent implements OnInit {
    receivingForm: FormGroup;
    po: PurchaseOrder;
    mode: 'receive' | 'correct';

    constructor(
        private fb: FormBuilder,
        private suppliersService: SuppliersService,
        public dialogRef: MatDialogRef<ReceivingDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: { po: PurchaseOrder, mode?: 'receive' | 'correct' }
    ) {
        this.po = data.po;
        this.mode = data.mode || 'receive';
        this.receivingForm = this.fb.group({
            reason: ['Receiving correction'],
            items: this.fb.array([])
        });
    }

    ngOnInit(): void {
        this.initFormItems();
    }

    get items(): FormArray {
        return this.receivingForm.get('items') as FormArray;
    }

    initFormItems() {
        this.po.items.forEach(item => {
            // Only show items that are not fully received? 
            // Or show all to allow correction/over-receiving?
            // Let's show all but default to remaining quantity.

            const remaining = Math.max(0, item.quantity_ordered - (item.quantity_received || 0));

            this.items.push(this.fb.group({
                po_item_id: [item.id || null],
                product_id: [item.product_id],
                variant_id: [item.variant_id || null],
                variant_name: [item.variant?.name || null],
                variant_sku: [item.variant?.sku || null],
                product_name: [item.product?.name || item.product_name || `Product #${item.product_id}`],
                quantity_ordered: [item.quantity_ordered],
                quantity_received_so_far: [item.quantity_received || 0],
                quantity_to_receive: [this.mode === 'receive' ? remaining : 0, [Validators.min(0)]]
            }));
        });
    }

    title(): string {
        return this.mode === 'correct' ? `Correct Receiving - PO #${this.po.id}` : `Receive Items - PO #${this.po.id}`;
    }

    quantityLabel(): string {
        return this.mode === 'correct' ? 'Reverse Received' : 'Receive Now';
    }

    submitLabel(): string {
        return this.mode === 'correct' ? 'Apply Correction' : 'Receive';
    }

    getImageUrl(product: any): string | null {
        if (!product || !product.images || product.images.length === 0) return null;

        // Find primary or first image
        const imgObj = product.images.find((img: any) => img.is_primary) || product.images[0];
        const path = typeof imgObj === 'string' ? imgObj : imgObj.image_path || imgObj.url;

        if (!path) return null;
        if (path.startsWith('http')) return path;
        if (path.startsWith('assets')) return path;

        // Normalize path
        let cleanPath = path.startsWith('/') ? path.substring(1) : path;

        // If it's in uploads directory
        if (cleanPath.startsWith('uploads')) {
            return `/${cleanPath}`;
        }

        // If it looks like a filename, assume product_images
        if (!cleanPath.includes('/')) {
            return `/uploads/product_images/${cleanPath}`;
        }

        return path;
    }

    getVariantName(item: PurchaseOrderItem): string | null {
        if (!item.variant_id || !item.product?.variants?.length) return null;
        return item.product.variants.find((variant: any) => variant.id === item.variant_id)?.name || null;
    }

    getVariantSku(item: PurchaseOrderItem): string | null {
        if (!item.variant_id || !item.product?.variants?.length) return null;
        return item.product.variants.find((variant: any) => variant.id === item.variant_id)?.sku || null;
    }

    onCancel(): void {
        this.dialogRef.close();
    }

    onSubmit(): void {
        if (this.receivingForm.valid) {
            const formValue = this.receivingForm.value;
            const itemsToSubmit = formValue.items
                .filter((item: any) => item.quantity_to_receive > 0)
                .map((item: any) => ({
                    po_item_id: item.po_item_id,
                    product_id: item.product_id,
                    variant_id: item.variant_id,
                    quantity: item.quantity_to_receive,
                    reason: this.mode === 'correct' ? formValue.reason : undefined
                }));

            if (itemsToSubmit.length === 0) {
                this.dialogRef.close();
                return;
            }

            const request$ = this.mode === 'correct'
                ? this.suppliersService.correctReceivedPurchaseOrderItems(this.po.id, itemsToSubmit)
                : this.suppliersService.receivePurchaseOrderItems(this.po.id, itemsToSubmit);

            request$
                .subscribe({
                    next: (updatedPo) => {
                        this.dialogRef.close(updatedPo);
                    },
                    error: (err) => {
                        console.error('Error receiving items:', err);
                        // Handle error (show message)
                    }
                });
        }
    }
}
