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
import { TranslocoModule } from '@ngneat/transloco';

export interface StockHistoryAdjustment {
  id: number;
  adjustment: number;
  reason: string | null;
  timestamp: string;
  created_by: string | null;
  /** Structured origin, e.g. 'purchase_order'. Null on legacy rows. */
  source?: string | null;
  /** Originating entity id, e.g. the PO id. Null on legacy rows. */
  source_id?: number | null;
}

export interface StockHistoryDialogData {
  productName: string;
  currentStock: number;
  inventoryAdjustments: StockHistoryAdjustment[];
}

/** Structured `source` value the PO-receiving write path stamps. */
const SOURCE_PURCHASE_ORDER = 'purchase_order';
/**
 * Legacy fallback: rows written before the structured `source` column
 * carry no `source`, but their `reason` is the server-side English
 * literal `"Received PO #<id>"` (it was never localized), so matching it
 * is safe for those historical rows. New rows use `source` instead.
 */
const LEGACY_PO_REASON_PREFIX = 'Received PO #';

@Component({
  selector: 'app-stock-history-dialog',
  standalone: true,
  imports: [TranslocoModule, 
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

  /** True when this adjustment came from PO receiving (or a correction). */
  isPoAdjustment(adj: StockHistoryAdjustment): boolean {
    return this.poId(adj) !== null;
  }

  /**
   * The linkable PO id: the structured `source_id` when present, else
   * the id parsed out of a legacy English `"Received PO #N"` reason.
   * Returns null when this isn't a PO adjustment.
   */
  poId(adj: StockHistoryAdjustment): number | null {
    if (adj.source === SOURCE_PURCHASE_ORDER && adj.source_id != null) {
      return adj.source_id;
    }
    // Legacy rows: no structured source, but the English reason carries
    // the id. (The reason is always English, so this is locale-safe.)
    if (!adj.source && adj.reason?.startsWith(LEGACY_PO_REASON_PREFIX)) {
      const match = adj.reason.match(/#(\d+)/);
      if (match) return Number(match[1]);
    }
    return null;
  }

  goToPo(adj: StockHistoryAdjustment): void {
    const id = this.poId(adj);
    if (id !== null) {
      this.onClose();
      this.router.navigate(['/suppliers/po', id]);
    }
  }
}