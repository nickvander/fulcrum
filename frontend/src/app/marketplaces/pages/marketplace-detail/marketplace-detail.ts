import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { TranslocoModule } from '@ngneat/transloco';
import { MarketplacesService, MarketplaceListing } from '../../marketplaces';
import { Observable, of } from 'rxjs';
import { ConfirmationDialog } from '../../../shared/components/confirmation-dialog/confirmation-dialog';

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
    MatTooltipModule,
    MatDialogModule,
    TranslocoModule
  ],
  templateUrl: './marketplace-detail.html',
  styleUrl: './marketplace-detail.scss',
})
export class MarketplaceDetailComponent implements OnInit {
  marketplaceId: string | null = null;
  listings$: Observable<MarketplaceListing[]> = of([]);
  displayedColumns: string[] = ['product', 'status', 'sync', 'price', 'actions'];

  disconnecting = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private marketplaceService: MarketplacesService,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
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

  disconnect(): void {
    if (!this.marketplaceId) {
      return;
    }
    const marketplaceId = parseInt(this.marketplaceId, 10);
    const ref = this.dialog.open(ConfirmationDialog, {
      data: {
        title: 'Disconnect marketplace',
        message:
          'This revokes the stored access token. Existing listings stay, but stock and price will not sync until you reconnect. Continue?'
      }
    });

    ref.afterClosed().subscribe((confirmed) => {
      if (!confirmed) {
        return;
      }

      this.disconnecting = true;
      this.marketplaceService.getCredentialForMarketplace(marketplaceId).subscribe({
        next: (credential) => {
          if (!credential) {
            this.disconnecting = false;
            this.snackBar.open('No stored credential to disconnect.', 'Close', { duration: 3000 });
            return;
          }
          this.marketplaceService.disconnectCredential(credential.id).subscribe({
            next: () => {
              this.disconnecting = false;
              this.snackBar.open('Marketplace disconnected.', 'Close', { duration: 3000 });
              this.router.navigate(['/marketplaces']);
            },
            error: (err) => {
              this.disconnecting = false;
              console.error('Disconnect error:', err);
              this.snackBar.open('Disconnect failed. Please try again.', 'Close', { duration: 5000 });
            }
          });
        },
        error: () => {
          this.disconnecting = false;
          this.snackBar.open('Could not look up credential.', 'Close', { duration: 3000 });
        }
      });
    });
  }
}
