import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { SupplierProduct } from '../../../shared/models/supplier-product.model';

@Component({
  selector: 'app-supplier-selection-dialog',
  standalone: false,
  templateUrl: './supplier-selection-dialog.component.html',
  styleUrls: ['./supplier-selection-dialog.component.scss']
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
