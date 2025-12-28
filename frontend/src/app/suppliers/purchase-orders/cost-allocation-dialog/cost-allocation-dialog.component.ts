import { Component, Inject, OnInit } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

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

    displayedColumns = ['product', 'qty', 'base', 'shipping', 'taxes', 'other', 'new_cost'];

    constructor(
        public dialogRef: MatDialogRef<CostAllocationDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: CostAllocationDialogData,
        private http: HttpClient
    ) { }

    ngOnInit(): void {
        this.loadPreview();
    }

    loadPreview(): void {
        this.loading = true;
        this.error = '';

        this.http.get<CostAllocationPreview>(
            `${environment.apiUrl}/purchase-orders/${this.data.poId}/costs/preview`
        ).subscribe({
            next: (preview) => {
                this.preview = preview;
                this.loading = false;
            },
            error: (err) => {
                this.error = err.error?.detail || 'Failed to load cost preview';
                this.loading = false;
            }
        });
    }

    getTotalAdditional(): number {
        if (!this.preview) return 0;
        return this.preview.total_shipping + this.preview.total_taxes + this.preview.total_other;
    }

    apply(): void {
        this.applying = true;

        this.http.post(
            `${environment.apiUrl}/purchase-orders/${this.data.poId}/costs/apply`,
            { confirm: true }
        ).subscribe({
            next: () => {
                this.dialogRef.close(true);
            },
            error: (err) => {
                this.error = err.error?.detail || 'Failed to apply costs';
                this.applying = false;
            }
        });
    }

    cancel(): void {
        this.dialogRef.close(false);
    }
}
