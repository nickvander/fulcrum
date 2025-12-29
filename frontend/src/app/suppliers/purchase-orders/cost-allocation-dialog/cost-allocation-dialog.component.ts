import { Component, Inject, OnInit } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { SuppliersService } from '../../suppliers.service';

export interface CostAllocationPreviewItem {
    item_id: number;
    product_name: string;
    quantity: number;
    current_unit_cost: number;
    base_cost: number;
    shipping_to_add: number;
    taxes_to_add: number;
    other_to_add: number;
    new_unit_cost: number;
}

export interface CostAllocationPreview {
    po_id: number;
    total_shipping: number;
    total_taxes: number;
    total_other: number;
    total_quantity: number;
    per_unit_shipping: number;
    per_unit_taxes: number;
    per_unit_other: number;
    items: CostAllocationPreviewItem[];
}

export interface CostAllocationDialogData {
    poId: number;
    overrides?: any;
}

@Component({
    selector: 'app-cost-allocation-dialog',
    templateUrl: './cost-allocation-dialog.component.html',
    styleUrls: ['./cost-allocation-dialog.component.scss'],
    standalone: false
})
export class CostAllocationDialogComponent implements OnInit {
    preview: CostAllocationPreview | null = null;
    loading = true;
    applying = false;
    error = '';
    excludedItems = new Set<number>();

    displayedColumns = ['select', 'product', 'qty', 'base', 'shipping', 'taxes', 'other', 'new_cost'];

    constructor(
        public dialogRef: MatDialogRef<CostAllocationDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: CostAllocationDialogData,
        private suppliersService: SuppliersService
    ) { }

    ngOnInit(): void {
        this.loadPreview();
    }

    loadPreview(): void {
        this.loading = true;
        this.error = '';

        this.suppliersService.getCostAllocationPreview(this.data.poId, Array.from(this.excludedItems), this.data.overrides)
            .subscribe({
                next: (preview: any) => {
                    this.preview = preview as CostAllocationPreview;
                    this.loading = false;
                },
                error: (err: any) => {
                    this.error = err.error?.detail || 'Failed to load cost preview';
                    this.loading = false;
                }
            });
    }

    toggleExclusion(itemId: number): void {
        if (this.excludedItems.has(itemId)) {
            this.excludedItems.delete(itemId);
        } else {
            this.excludedItems.add(itemId);
        }
        this.loadPreview();
    }

    getTotalAdditional(): number {
        if (!this.preview) return 0;
        return this.preview.total_shipping + this.preview.total_taxes + this.preview.total_other;
    }

    apply(): void {
        this.applying = true;

        this.suppliersService.applyCostAllocation(this.data.poId, Array.from(this.excludedItems))
            .subscribe({
                next: () => {
                    this.dialogRef.close(true);
                },
                error: (err: any) => {
                    this.error = err.error?.detail || 'Failed to apply costs';
                    this.applying = false;
                }
            });
    }

    cancel(): void {
        this.dialogRef.close(false);
    }
}
