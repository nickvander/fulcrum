import { Component, Inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';

export interface StockAdjustmentData {
  productName: string;
  currentQuantity: number;
}

@Component({
  selector: 'app-stock-adjustment-dialog',
  templateUrl: './stock-adjustment-dialog.html',
  styleUrls: ['./stock-adjustment-dialog.scss'],
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
  ],
})
export class StockAdjustmentDialog {
  adjustment = 0;

  constructor(
    public dialogRef: MatDialogRef<StockAdjustmentDialog>,
    @Inject(MAT_DIALOG_DATA) public data: StockAdjustmentData
  ) {}

  onCancel(): void {
    this.dialogRef.close();
  }
}
