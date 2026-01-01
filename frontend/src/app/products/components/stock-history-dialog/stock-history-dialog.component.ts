import { Component, Inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { CommonModule } from '@angular/common';
import { MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { OrderByPipe } from '../../pipes/order-by.pipe';
import { DatePipe } from '@angular/common';
import { Router } from '@angular/router';

export interface StockHistoryDialogData {
  productName: string;
  currentStock: number;
  inventoryAdjustments: Array<{
    id: number;
    adjustment: number;
    reason: string | null;
    timestamp: string;
    created_by: string | null;
  }>;
}

@Component({
  selector: 'app-stock-history-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatListModule,
    MatIconModule,
    OrderByPipe,
    DatePipe
  ],
  templateUrl: './stock-history-dialog.component.html',
  styleUrls: ['./stock-history-dialog.component.scss']
})
export class StockHistoryDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<StockHistoryDialogComponent>,
    private router: Router,
    @Inject(MAT_DIALOG_DATA) public data: StockHistoryDialogData
  ) { }

  onClose(): void {
    this.dialogRef.close();
  }

  isPoReason(reason: string | null): boolean {
    return !!reason && reason.startsWith('Received PO #');
  }

  getPoLabel(reason: string): string {
    return reason;
  }

  goToPo(reason: string): void {
    const match = reason.match(/#(\d+)/);
    if (match && match[1]) {
      this.onClose();
      this.router.navigate(['/suppliers/po', match[1]]);
    }
  }
}