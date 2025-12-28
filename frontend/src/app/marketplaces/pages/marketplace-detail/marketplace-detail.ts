import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MarketplacesService, MarketplaceListing } from '../../marketplaces';
import { Observable, of } from 'rxjs';

@Component({
  selector: 'app-marketplace-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatSnackBarModule,
    MatTooltipModule
  ],
  template: `
    <div class="detail-container">
      <nav class="breadcrumb">
        <a routerLink="/marketplaces" class="back-link">
          <mat-icon>arrow_back</mat-icon>
          <span>Marketplace Channels</span>
        </a>
      </nav>

      <div class="page-header">
        <div class="header-text">
          <h1>Channel Listings</h1>
          <p>Review and manage individual product status for Channel: <strong>#{{ marketplaceId }}</strong></p>
        </div>
        <div class="header-actions">
          <button mat-stroked-button color="warn" (click)="comingSoon('Disconnect')">
            <mat-icon>link_off</mat-icon>
            Disconnect
          </button>
          <button mat-flat-button color="primary" (click)="comingSoon('Bulk Sync')">
            <mat-icon>sync</mat-icon>
            Bulk Re-Sync
          </button>
        </div>
      </div>

      <div class="table-card mat-elevation-z2">
        <mat-table [dataSource]="(listings$ | async) || []">
          <!-- Product ID Column -->
          <ng-container matColumnDef="product">
            <mat-header-cell *matHeaderCellDef> Product Entity </mat-header-cell>
            <mat-cell *matCellDef="let listing"> 
              <div class="product-info">
                <span class="product-id">Product #{{ listing.product_id }}</span>
                <span class="external-id">Marketplace Ref: {{ listing.external_listing_id || 'N/A' }}</span>
              </div>
            </mat-cell>
          </ng-container>

          <!-- Status Column -->
          <ng-container matColumnDef="status">
            <mat-header-cell *matHeaderCellDef> Channel Status </mat-header-cell>
            <mat-cell *matCellDef="let listing">
              <mat-chip-set>
                <mat-chip class="listing-status-chip" [ngClass]="listing.status">{{ listing.status | titlecase }}</mat-chip>
              </mat-chip-set>
            </mat-cell>
          </ng-container>

          <!-- Sync Column -->
          <ng-container matColumnDef="sync">
            <mat-header-cell *matHeaderCellDef> Sync Health </mat-header-cell>
            <mat-cell *matCellDef="let listing">
              <div class="sync-status">
                <mat-icon [ngClass]="listing.sync_status === 'IN_SYNC' ? 'success' : 'warning'">
                  {{ listing.sync_status === 'IN_SYNC' ? 'check_circle' : 'sync_problem' }}
                </mat-icon>
                <span>{{ listing.sync_status === 'IN_SYNC' ? 'Synced' : (listing.sync_status || 'Pending') }}</span>
              </div>
            </mat-cell>
          </ng-container>

          <!-- Price Column -->
          <ng-container matColumnDef="price">
            <mat-header-cell *matHeaderCellDef> Marketplace Price </mat-header-cell>
            <mat-cell *matCellDef="let listing"> 
              <span class="price-value">{{ listing.marketplace_price | currency:'USD' }}</span>
            </mat-cell>
          </ng-container>

          <!-- Actions Column -->
          <ng-container matColumnDef="actions">
            <mat-header-cell *matHeaderCellDef> </mat-header-cell>
            <mat-cell *matCellDef="let listing">
              <button mat-icon-button color="primary" matTooltip="Force Individual Sync" (click)="comingSoon('Manual Sync')">
                <mat-icon>sync</mat-icon>
              </button>
              @if (listing.listing_url) {
                <a mat-icon-button [href]="listing.listing_url" target="_blank" matTooltip="Open on Marketplace">
                  <mat-icon>open_in_new</mat-icon>
                </a>
              }
            </mat-cell>
          </ng-container>

          <mat-header-row *matHeaderRowDef="displayedColumns"></mat-header-row>
          <mat-row *matRowDef="let row; columns: displayedColumns;"></mat-row>
        </mat-table>

        @if (!((listings$ | async)?.length)) {
          <div class="empty-table">
            <mat-icon>info</mat-icon>
            <p>No active listings found for this channel. Start by pushing products from the Inventory manager.</p>
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .detail-container {
      padding: 2rem;
      max-width: 1400px;
      margin: 0 auto;
    }
    .breadcrumb {
      margin-bottom: 2rem;
    }
    .back-link {
      display: inline-flex;
      align-items: center;
      text-decoration: none;
      color: #64748b;
      font-weight: 500;
      transition: color 0.2s;
    }
    .back-link:hover {
      color: #0f172a;
    }
    .back-link mat-icon {
      margin-right: 8px;
      font-size: 20px;
      width: 20px;
      height: 20px;
    }
    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      margin-bottom: 2rem;
    }
    .header-text h1 {
      font-size: 2rem;
      font-weight: 800;
      color: #1e293b;
      margin: 0 0 0.5rem 0;
    }
    .header-text p {
      color: #64748b;
      margin: 0;
    }
    .header-actions button {
      margin-left: 1rem;
    }
    .table-card {
      background: white;
      border-radius: 16px;
      overflow: hidden;
      border: 1px solid rgba(0,0,0,0.05);
    }
    mat-table {
      background: transparent;
    }
    mat-header-row {
      background: #f8fafc;
      min-height: 56px;
    }
    mat-row {
      min-height: 72px;
      border-bottom: 1px solid #f1f5f9;
      transition: background 0.2s;
    }
    mat-row:hover {
      background: #fdfdfd;
    }
    .product-info {
      display: flex;
      flex-direction: column;
    }
    .product-id {
      font-weight: 600;
      color: #0f172a;
      font-size: 0.95rem;
    }
    .external-id {
      font-size: 0.75rem;
      color: #64748b;
    }
    .listing-status-chip {
      font-size: 11px;
      height: 24px;
    }
    .listing-status-chip.active {
      background-color: #f0fdf4;
      color: #166534;
    }
    .sync-status {
      display: flex;
      align-items: center;
      font-size: 0.875rem;
      font-weight: 500;
    }
    .sync-status mat-icon {
      margin-right: 6px;
      font-size: 18px;
      width: 18px;
      height: 18px;
    }
    .sync-status mat-icon.success { color: #22c55e; }
    .sync-status mat-icon.warning { color: #f59e0b; }
    .price-value {
      font-weight: 700;
      color: #0f172a;
    }
    .empty-table {
      padding: 4rem 2rem;
      text-align: center;
      color: #64748b;
    }
    .empty-table mat-icon {
      font-size: 40px;
      width: 40px;
      height: 40px;
      margin-bottom: 1rem;
      color: #cbd5e1;
    }
  `],
})
export class MarketplaceDetailComponent implements OnInit {
  marketplaceId: string | null = null;
  listings$: Observable<MarketplaceListing[]> = of([]);
  displayedColumns: string[] = ['product', 'status', 'sync', 'price', 'actions'];

  constructor(
    private route: ActivatedRoute,
    private marketplaceService: MarketplacesService,
    private snackBar: MatSnackBar
  ) { }

  ngOnInit(): void {
    this.marketplaceId = this.route.snapshot.paramMap.get('id');
    this.listings$ = this.marketplaceService.getMarketplaceListings();
  }

  comingSoon(feature: string): void {
    this.snackBar.open(`${feature} functionality is coming soon!`, 'Close', {
      duration: 3000,
      horizontalPosition: 'right',
      verticalPosition: 'top'
    });
  }
}
