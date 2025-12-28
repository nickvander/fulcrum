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
  templateUrl: './marketplace-detail.html',
  styleUrl: './marketplace-detail.scss',
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

  syncListing(listingId: number): void {
    this.marketplaceService.syncListing(listingId).subscribe({
      next: () => {
        this.snackBar.open('Listing synced successfully!', 'Close', { duration: 3000 });
        this.listings$ = this.marketplaceService.getMarketplaceListings();
      },
      error: (err) => {
        console.error('Sync error:', err);
        this.snackBar.open('Sync failed. Please try again.', 'Close', { duration: 5000 });
      }
    });
  }

  syncAll(): void {
    this.snackBar.open('Bulk sync initiated...', '', { duration: 2000 });
    // This would call the import endpoint for this marketplace
    if (this.marketplaceId) {
      this.marketplaceService.importListings(parseInt(this.marketplaceId)).subscribe({
        next: (stats) => {
          const msg = `Sync complete! Synced: ${stats.synced}, Created: ${stats.created_product_shell}`;
          this.snackBar.open(msg, 'Close', { duration: 5000 });
          this.listings$ = this.marketplaceService.getMarketplaceListings();
        },
        error: (err) => {
          console.error('Bulk sync error:', err);
          this.snackBar.open('Bulk sync failed.', 'Close', { duration: 5000 });
        }
      });
    }
  }

  comingSoon(feature: string): void {
    this.snackBar.open(`${feature} functionality is coming soon!`, 'Close', {
      duration: 3000,
      horizontalPosition: 'right',
      verticalPosition: 'top'
    });
  }
}
