import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { SupplierProduct } from '../../../shared/models/supplier-product.model';

@Component({
    selector: 'app-supplier-selection-dialog',
    standalone: false,
    template: `
    <h2 mat-dialog-title>Select Supplier for {{ data.productName }}</h2>
    <div mat-dialog-content>
      <p style="margin-bottom: 16px;">This product is available from multiple suppliers. Which one would you like to use for this order?</p>
      
      <mat-list>
        <mat-list-item *ngFor="let sp of data.suppliers" (click)="select(sp)" class="supplier-option">
          <span matListItemIcon>
            <mat-icon>store</mat-icon>
          </span>
          <div matListItemTitle>{{ sp.supplier_name }}</div>
          <div matListItemLine>
            Cost: {{ sp.cost_price | currency }} | 
            Lead Time: {{ sp.lead_time_days || '?' }} days | 
            SKU: {{ sp.supplier_sku }}
          </div>
          <button mat-icon-button matListItemMeta>
            <mat-icon>chevron_right</mat-icon>
          </button>
        </mat-list-item>
      </mat-list>
    </div>
    <div mat-dialog-actions align="end">
      <button mat-button (click)="cancel()">Cancel</button>
    </div>
  `,
    styles: [`
    .supplier-option {
      cursor: pointer;
      border-radius: 4px;
      margin-bottom: 4px;
    }
    .supplier-option:hover {
      background-color: rgba(0,0,0,0.04);
    }
  `]
})
export class SupplierSelectionDialogComponent {
    constructor(
        public dialogRef: MatDialogRef<SupplierSelectionDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: { productName: string, suppliers: SupplierProduct[] }
    ) { }

    select(sp: SupplierProduct): void {
        this.dialogRef.close(sp);
    }

    cancel(): void {
        this.dialogRef.close(null);
    }
}
