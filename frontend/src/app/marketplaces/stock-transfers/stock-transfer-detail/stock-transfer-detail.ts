import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { TranslocoModule } from '@ngneat/transloco';

import {
  STOCK_LOCATION_AMAZON_FBA,
  STOCK_LOCATION_ML_FULL,
  StockTransfer,
  StockTransferService,
  SyncListingsResult,
} from '../stock-transfer.service';
import { ReceiveTransferDialogComponent } from '../receive-transfer-dialog/receive-transfer-dialog';

@Component({
  selector: 'app-stock-transfer-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatDialogModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTableModule,
    TranslocoModule,
  ],
  templateUrl: './stock-transfer-detail.html',
  styleUrl: './stock-transfer-detail.scss',
})
export class StockTransferDetailComponent implements OnInit {
  transfer: StockTransfer | null = null;
  loading = false;
  acting = false;
  lastSync: SyncListingsResult | null = null;
  readonly columns = ['product', 'qty_planned', 'qty_shipped', 'qty_received'];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private service: StockTransferService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (id) {
      this.load(id);
    }
  }

  load(id: number): void {
    this.loading = true;
    this.service.get(id).subscribe({
      next: transfer => {
        this.transfer = transfer;
        this.loading = false;
      },
      error: err => {
        console.error('Load transfer failed', err);
        this.loading = false;
        this.snackBar.open('Failed to load transfer', 'Close', { duration: 4000 });
      },
    });
  }

  ship(pushToMarketplace = false): void {
    if (!this.transfer || this.acting) {
      return;
    }
    this.acting = true;
    this.service.ship(this.transfer.id, pushToMarketplace).subscribe({
      next: updated => {
        this.transfer = updated;
        this.acting = false;
        const message = pushToMarketplace
          ? 'Shipped and inbound shipment reserved'
          : 'Marked as shipped';
        this.snackBar.open(message, 'Close', { duration: 3000 });
      },
      error: err => {
        this.acting = false;
        // HttpErrorInterceptor surfaces the localized backend message.
      },
    });
  }

  syncListings(): void {
    if (!this.transfer || this.acting) {
      return;
    }
    this.acting = true;
    this.service.syncListings(this.transfer.id).subscribe({
      next: summary => {
        this.acting = false;
        this.lastSync = summary;
        if (summary.needs_reauthorization) {
          this.snackBar.open(
            `Reauthorize ${summary.marketplace || 'marketplace'} before syncing`,
            'Close',
            { duration: 5000 },
          );
          return;
        }
        const okCount = summary.updated.filter(u => u.ok).length;
        const total = summary.updated.length;
        const missing = summary.missing_listings.length;
        const parts: string[] = [];
        if (total > 0) {
          parts.push(`${okCount}/${total} listings synced`);
        }
        if (missing > 0) {
          parts.push(`${missing} need a listing`);
        }
        this.snackBar.open(parts.join(' · ') || 'Nothing to sync', 'Close', {
          duration: 4000,
        });
      },
      error: err => {
        this.acting = false;
        // HttpErrorInterceptor surfaces the localized backend message.
      },
    });
  }

  isMarketplaceDestination(): boolean {
    return (
      !!this.transfer &&
      (this.transfer.dest_location === STOCK_LOCATION_ML_FULL ||
        this.transfer.dest_location === STOCK_LOCATION_AMAZON_FBA)
    );
  }

  canSyncListings(): boolean {
    return (
      !!this.transfer &&
      this.isMarketplaceDestination() &&
      (this.transfer.status === 'received' ||
        this.transfer.status === 'partially_received') &&
      !this.acting
    );
  }

  openReceive(): void {
    if (!this.transfer) {
      return;
    }
    const ref = this.dialog.open(ReceiveTransferDialogComponent, {
      width: '720px',
      data: { transfer: this.transfer },
    });
    ref.afterClosed().subscribe(updated => {
      if (updated) {
        this.transfer = updated;
      }
    });
  }

  cancelTransfer(): void {
    if (!this.transfer || this.acting) {
      return;
    }
    this.acting = true;
    this.service.cancel(this.transfer.id).subscribe({
      next: updated => {
        this.transfer = updated;
        this.acting = false;
        this.snackBar.open('Transfer cancelled', 'Close', { duration: 3000 });
      },
      error: err => {
        this.acting = false;
        // HttpErrorInterceptor surfaces the localized backend message.
      },
    });
  }

  deleteTransfer(): void {
    if (!this.transfer || this.acting) {
      return;
    }
    this.acting = true;
    const id = this.transfer.id;
    this.service.delete(id).subscribe({
      next: () => {
        this.acting = false;
        this.snackBar.open('Transfer deleted', 'Close', { duration: 3000 });
        this.router.navigate(['/marketplaces/transfers']);
      },
      error: err => {
        this.acting = false;
        // HttpErrorInterceptor surfaces the localized backend message.
      },
    });
  }

  totalPlanned(): number {
    return this.transfer?.items.reduce((sum, item) => sum + (item.qty_planned || 0), 0) || 0;
  }

  totalReceived(): number {
    return this.transfer?.items.reduce((sum, item) => sum + (item.qty_received || 0), 0) || 0;
  }

  canShip(): boolean {
    return !!this.transfer && this.transfer.status === 'draft' && !this.acting;
  }

  canReceive(): boolean {
    return (
      !!this.transfer &&
      (this.transfer.status === 'shipped' || this.transfer.status === 'partially_received') &&
      !this.acting
    );
  }

  canCancel(): boolean {
    return !!this.transfer && this.transfer.status === 'draft' && !this.acting;
  }

  canDelete(): boolean {
    return (
      !!this.transfer &&
      (this.transfer.status === 'draft' || this.transfer.status === 'cancelled') &&
      !this.acting
    );
  }
}
