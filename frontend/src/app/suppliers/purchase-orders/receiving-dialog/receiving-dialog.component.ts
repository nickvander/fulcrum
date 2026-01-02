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

    constructor(
        private fb: FormBuilder,
        private suppliersService: SuppliersService,
        public dialogRef: MatDialogRef<ReceivingDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: { po: PurchaseOrder }
    ) {
        this.po = data.po;
        this.receivingForm = this.fb.group({
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
                product_id: [item.product_id],
                product_name: [item.product_id], // todo: need product name lookup or enrichment
                quantity_ordered: [item.quantity_ordered],
                quantity_received_so_far: [item.quantity_received || 0],
                quantity_to_receive: [remaining, [Validators.min(0)]]
            }));
        });
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

    onCancel(): void {
        this.dialogRef.close();
    }

    onSubmit(): void {
        if (this.receivingForm.valid) {
            const formValue = this.receivingForm.value;
            const itemsToReceive = formValue.items
                .filter((item: any) => item.quantity_to_receive > 0)
                .map((item: any) => ({
                    product_id: item.product_id,
                    quantity: item.quantity_to_receive
                }));

            if (itemsToReceive.length === 0) {
                // Nothing to receive
                this.dialogRef.close();
                return;
            }

            this.suppliersService.receivePurchaseOrderItems(this.po.id, itemsToReceive)
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
