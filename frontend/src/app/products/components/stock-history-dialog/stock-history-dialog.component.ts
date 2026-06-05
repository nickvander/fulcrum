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

/**
 * Resolved origin of an adjustment for display: a localized label + an
 * optional entity id + optional routerLink commands. `commands === null`
 * renders a plain chip (no link); a non-null `id` is shown as "#id".
 */
export interface AdjustmentOrigin {
  labelKey: string;
  id: number | null;
  commands: unknown[] | null;
}

/**
 * Per-`source` display config. `route` builds the routerLink commands for
 * the linkable origins; sources without a `route` render as a plain chip.
 * Keys mirror `InventoryAdjustmentSource` on the backend.
 */
const SOURCE_CONFIG: Record<
  string,
  { labelKey: string; route?: (id: number) => unknown[] }
> = {
  purchase_order: {
    labelKey: 'products.stockHistoryDialog.receivedPo',
    route: id => ['/suppliers/po', id],
  },
  stock_transfer: {
    labelKey: 'products.stockHistoryDialog.fromTransfer',
    route: id => ['/marketplaces/transfers', id],
  },
  sales_order: {
    labelKey: 'products.stockHistoryDialog.fromOrder',
    route: id => ['/orders', id],
  },
  inventory_count: {
    labelKey: 'products.stockHistoryDialog.fromCount',
    route: id => ['/inventory/count', id],
  },
  bundle_assembly: { labelKey: 'products.stockHistoryDialog.fromBundle' },
  marketplace_sync: { labelKey: 'products.stockHistoryDialog.fromMarketplaceSync' },
  adjustment_reversal: { labelKey: 'products.stockHistoryDialog.fromReversal' },
};

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

  /**
   * Resolve the structured origin of an adjustment, or null when it has
   * none (a plain manual edit). Reads the structured `source`/`source_id`
   * — never the localized `reason` — except for the one legacy fallback
   * below. Drives the origin chip + its optional deep-link.
   */
  origin(adj: StockHistoryAdjustment): AdjustmentOrigin | null {
    if (adj.source) {
      const config = SOURCE_CONFIG[adj.source];
      if (!config) return null; // unknown/future source → plain reason text
      const id = adj.source_id ?? null;
      return {
        labelKey: config.labelKey,
        id,
        commands: config.route && id != null ? config.route(id) : null,
      };
    }
    // Legacy rows: no structured source, but the English reason carries
    // the PO id. (The reason is always English, so this stays locale-safe.)
    if (adj.reason?.startsWith(LEGACY_PO_REASON_PREFIX)) {
      const match = adj.reason.match(/#(\d+)/);
      if (match) {
        const id = Number(match[1]);
        return {
          labelKey: 'products.stockHistoryDialog.receivedPo',
          id,
          commands: ['/suppliers/po', id],
        };
      }
    }
    return null;
  }

  goToOrigin(o: AdjustmentOrigin): void {
    if (o.commands) {
      this.onClose();
      this.router.navigate(o.commands);
    }
  }
}