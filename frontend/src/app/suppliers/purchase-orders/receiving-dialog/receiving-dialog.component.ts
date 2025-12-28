import { Component, Inject, OnInit } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { FormBuilder, FormGroup, FormArray, Validators } from '@angular/forms';
import { PurchaseOrder, PurchaseOrderItem } from '../../../shared/models/purchase-order.model';
import { SuppliersService } from '../../suppliers.service';

@Component({
    selector: 'app-receiving-dialog',
    templateUrl: './receiving-dialog.component.html',
    styleUrls: ['./receiving-dialog.component.scss'],
    standalone: false
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
