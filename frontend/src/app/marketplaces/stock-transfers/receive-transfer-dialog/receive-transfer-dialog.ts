import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { TranslocoModule } from '@ngneat/transloco';

import {
  StockTransfer,
  StockTransferReceiveLine,
  StockTransferService,
} from '../stock-transfer.service';

interface ReceiveRow {
  transferItemId: number;
  productId: number;
  productName: string;
  qtyShipped: number;
  qtyReceived: number;
  remaining: number;
  toReceive: number;
}

@Component({
  selector: 'app-receive-transfer-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSnackBarModule,
    MatTableModule,
    TranslocoModule,
  ],
  templateUrl: './receive-transfer-dialog.html',
  styleUrl: './receive-transfer-dialog.scss',
})
export class ReceiveTransferDialogComponent {
  rows: ReceiveRow[];
  saving = false;
  readonly columns = ['product', 'shipped', 'received', 'toReceive'];

  constructor(
    public dialogRef: MatDialogRef<ReceiveTransferDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { transfer: StockTransfer },
    private service: StockTransferService,
    private snackBar: MatSnackBar,
  ) {
    this.rows = this.data.transfer.items.map(item => {
      const remaining = Math.max(0, (item.qty_shipped || 0) - (item.qty_received || 0));
      return {
        transferItemId: item.id,
        productId: item.product_id,
        productName: item.product?.name || `Product #${item.product_id}`,
        qtyShipped: item.qty_shipped || 0,
        qtyReceived: item.qty_received || 0,
        remaining,
        toReceive: remaining,
      };
    });
  }

  updateToReceive(row: ReceiveRow, value: string | number): void {
    const next = Number(value);
    if (!Number.isFinite(next) || next < 0) {
      row.toReceive = 0;
    } else {
      row.toReceive = Math.min(Math.floor(next), row.remaining);
    }
  }

  canSave(): boolean {
    return (
      !this.saving &&
      this.rows.some(row => row.toReceive > 0) &&
      this.rows.every(row => row.toReceive <= row.remaining)
    );
  }

  save(): void {
    if (!this.canSave()) {
      return;
    }
    this.saving = true;
    const lines: StockTransferReceiveLine[] = this.rows
      .filter(row => row.toReceive > 0)
      .map(row => ({
        transfer_item_id: row.transferItemId,
        product_id: row.productId,
        quantity: row.toReceive,
      }));

    this.service.receive(this.data.transfer.id, lines).subscribe({
      next: updated => {
        this.saving = false;
        this.snackBar.open('Receipt recorded', 'Close', { duration: 3000 });
        this.dialogRef.close(updated);
      },
      error: err => {
        console.error('Receive failed', err);
        this.saving = false;
        // HttpErrorInterceptor surfaces the localized backend message.
      },
    });
  }

  cancel(): void {
    this.dialogRef.close();
  }
}
