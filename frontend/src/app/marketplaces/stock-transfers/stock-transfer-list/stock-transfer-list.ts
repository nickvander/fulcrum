import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { TranslocoModule } from '@ngneat/transloco';
import { Router } from '@angular/router';

import {
  StockTransfer,
  StockTransferService,
  StockTransferStatus,
} from '../stock-transfer.service';
import { StockTransferCreateDialogComponent } from '../stock-transfer-create-dialog/stock-transfer-create-dialog';

const STATUS_FILTERS: { key: string; status: StockTransferStatus | null }[] = [
  { key: 'all', status: null },
  { key: 'draft', status: 'draft' },
  { key: 'shipped', status: 'shipped' },
  { key: 'partially_received', status: 'partially_received' },
  { key: 'received', status: 'received' },
  { key: 'cancelled', status: 'cancelled' },
];

@Component({
  selector: 'app-stock-transfer-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatIconModule,
    MatTableModule,
    MatTabsModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatDialogModule,
    TranslocoModule,
  ],
  templateUrl: './stock-transfer-list.html',
  styleUrl: './stock-transfer-list.scss',
})
export class StockTransferListComponent implements OnInit {
  transfers: StockTransfer[] = [];
  loading = false;
  selectedFilter: StockTransferStatus | null = null;
  readonly statusFilters = STATUS_FILTERS;
  readonly displayedColumns = [
    'id',
    'status',
    'route',
    'units',
    'created_at',
    'actions',
  ];

  constructor(
    private service: StockTransferService,
    private router: Router,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    this.reload();
  }

  onFilterChange(index: number): void {
    this.selectedFilter = this.statusFilters[index].status;
    this.reload();
  }

  reload(): void {
    this.loading = true;
    this.service.list(this.selectedFilter).subscribe({
      next: transfers => {
        this.transfers = transfers;
        this.loading = false;
      },
      error: err => {
        console.error('Stock transfer list failed', err);
        this.loading = false;
        this.snackBar.open('Failed to load stock transfers', 'Close', { duration: 4000 });
      },
    });
  }

  unitsPlanned(transfer: StockTransfer): number {
    return transfer.items.reduce((sum, item) => sum + (item.qty_planned || 0), 0);
  }

  unitsReceived(transfer: StockTransfer): number {
    return transfer.items.reduce((sum, item) => sum + (item.qty_received || 0), 0);
  }

  statusColor(status: StockTransferStatus): string {
    switch (status) {
      case 'draft':
        return 'primary';
      case 'shipped':
      case 'partially_received':
        return 'accent';
      case 'received':
        return 'primary';
      case 'cancelled':
        return 'warn';
      default:
        return '';
    }
  }

  openCreate(): void {
    const ref = this.dialog.open(StockTransferCreateDialogComponent, {
      width: '720px',
      maxHeight: '90vh',
    });
    ref.afterClosed().subscribe(created => {
      if (created) {
        this.router.navigate(['/marketplaces/transfers', created.id]);
      }
    });
  }

  view(transfer: StockTransfer): void {
    this.router.navigate(['/marketplaces/transfers', transfer.id]);
  }
}
