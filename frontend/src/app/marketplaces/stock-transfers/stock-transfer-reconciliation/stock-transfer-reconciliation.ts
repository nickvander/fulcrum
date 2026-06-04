import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';

import {
  ReconciliationRow,
  StockTransferService,
} from '../stock-transfer.service';

@Component({
  selector: 'app-stock-transfer-reconciliation',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTableModule,
    TranslocoModule,
  ],
  templateUrl: './stock-transfer-reconciliation.html',
  styleUrl: './stock-transfer-reconciliation.scss',
})
export class StockTransferReconciliationComponent implements OnInit {
  rows: ReconciliationRow[] = [];
  loading = false;
  readonly columns = [
    'transfer',
    'product',
    'destination',
    'shipped',
    'received',
    'delta',
  ];

  constructor(
    private service: StockTransferService,
    private snackBar: MatSnackBar,
    private transloco: TranslocoService,
  ) {}

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.loading = true;
    this.service.reconciliation().subscribe({
      next: rows => {
        this.rows = rows;
        this.loading = false;
      },
      error: err => {
        console.error('Reconciliation load failed', err);
        this.loading = false;
        this.snackBar.open(
          this.transloco.translate('stockTransfers.stockTransferReconciliation.loadFailed'),
          this.transloco.translate('common.close'),
          { duration: 4000 },
        );
      },
    });
  }

  totalDelta(): number {
    return this.rows.reduce((sum, r) => sum + r.delta, 0);
  }

  shrinkRowClass(row: ReconciliationRow): string {
    if (row.delta < 0) return 'delta-negative';
    if (row.delta > 0) return 'delta-positive';
    return '';
  }

  /**
   * A reconciliation row is a *settled discrepancy* worth a "Discrepancia"
   * flag when its shipped↔received gap is materially large — mirroring the
   * cycle-count variance tolerance (>10 units OR >5% of shipped) so the two
   * surfaces read the same.
   *
   * Over-receipts (received > shipped) always count: receiving more than was
   * shipped is wrong in any state. A shortfall (received < shipped) only
   * counts once the receive window has closed (RECEIVED / CANCELLED); on a
   * PARTIALLY_RECEIVED transfer a shortfall may simply still be in transit,
   * so we don't cry wolf.
   */
  private static readonly VARIANCE_ABS = 10;
  private static readonly VARIANCE_PCT = 0.05;

  isDiscrepancy(row: ReconciliationRow): boolean {
    if (row.delta === 0) return false;
    if (row.delta < 0 && row.transfer_status === 'partially_received') {
      return false; // shortfall may still be in transit — not settled
    }
    const abs = Math.abs(row.delta);
    const pct = row.qty_shipped > 0 ? abs / row.qty_shipped : 1;
    return (
      abs > StockTransferReconciliationComponent.VARIANCE_ABS ||
      pct > StockTransferReconciliationComponent.VARIANCE_PCT
    );
  }

  /** Signed delta for the flag label, e.g. '+12' / '-15'. */
  discrepancyLabel(row: ReconciliationRow): string {
    return (row.delta > 0 ? '+' : '') + row.delta;
  }

  discrepancyCount(): number {
    return this.rows.filter(r => this.isDiscrepancy(r)).length;
  }
}
