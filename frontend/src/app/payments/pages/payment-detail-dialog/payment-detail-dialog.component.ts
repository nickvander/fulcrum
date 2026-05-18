import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { TranslocoModule } from '@ngneat/transloco';

import { Payment } from '../../services/payments.service';

export interface PaymentDetailDialogData {
  payment: Payment;
}

@Component({
  selector: 'app-payment-detail-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatDialogModule,
    MatDividerModule,
    MatIconModule,
    TranslocoModule,
  ],
  templateUrl: './payment-detail-dialog.component.html',
  styleUrls: ['./payment-detail-dialog.component.scss'],
})
export class PaymentDetailDialogComponent {
  payment: Payment;

  constructor(
    public dialogRef: MatDialogRef<PaymentDetailDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: PaymentDetailDialogData,
  ) {
    this.payment = data.payment;
  }

  close(): void {
    this.dialogRef.close();
  }

  formatTimestamp(iso: string | null | undefined): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleString();
  }

  formatJson(obj: Record<string, unknown> | null): string {
    if (!obj) return '';
    return JSON.stringify(obj, null, 2);
  }

  statusClass(status: string): string {
    return `status-${status}`;
  }
}
