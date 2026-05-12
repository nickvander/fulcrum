import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { TranslocoModule } from '@ngneat/transloco';

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
        this.snackBar.open('Failed to load reconciliation', 'Close', {
          duration: 4000,
        });
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
}
