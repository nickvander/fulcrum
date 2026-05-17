import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { SupplierProduct } from '../../../shared/models/supplier-product.model';
import { TranslocoModule } from '@ngneat/transloco';

@Component({
  selector: 'app-supplier-selection-dialog',
  standalone: true,
  imports: [TranslocoModule, CommonModule, MatDialogModule, MatButtonModule, MatIconModule, MatListModule],
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
