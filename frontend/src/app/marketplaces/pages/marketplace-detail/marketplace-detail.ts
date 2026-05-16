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
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
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
    private dialog: MatDialog,
    private transloco: TranslocoService
  ) { }

  private t(key: string, params?: Record<string, unknown>): string {
    return this.transloco.translate(key, params);
  }

  private get closeLabel(): string {
    return this.t('common.close');
  }

  ngOnInit(): void {
    this.marketplaceId = this.route.snapshot.paramMap.get('id');
    this.listings$ = this.marketplaceService.getMarketplaceListings();
  }

  syncListing(listingId: number): void {
    this.marketplaceService.syncListing(listingId).subscribe({
      next: () => {
        this.snackBar.open(this.t('marketing.messages.listingSynced'), this.closeLabel, { duration: 3000 });
        this.listings$ = this.marketplaceService.getMarketplaceListings();
      },
      error: (err) => {
        console.error('Sync error:', err);
        this.snackBar.open(this.t('marketing.messages.listingSyncFailed'), this.closeLabel, { duration: 5000 });
      }
    });
  }

  syncAll(): void {
    this.snackBar.open(this.t('marketing.messages.bulkSyncInitiated'), '', { duration: 2000 });
    if (this.marketplaceId) {
      this.marketplaceService.importListings(parseInt(this.marketplaceId)).subscribe({
        next: (stats) => {
          const msg = this.t('marketing.messages.syncCompleteSummary', {
            synced: stats.synced,
            created: stats.created_product_shell,
          });
          this.snackBar.open(msg, this.closeLabel, { duration: 5000 });
          this.listings$ = this.marketplaceService.getMarketplaceListings();
        },
        error: (err) => {
          console.error('Bulk sync error:', err);
          this.snackBar.open(this.t('marketing.messages.bulkSyncFailed'), this.closeLabel, { duration: 5000 });
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
        title: this.t('marketing.disconnectDialog.title'),
        message: this.t('marketing.disconnectDialog.message'),
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
            this.snackBar.open(this.t('marketing.messages.noCredentialToDisconnect'), this.closeLabel, { duration: 3000 });
            return;
          }
          this.marketplaceService.disconnectCredential(credential.id).subscribe({
            next: () => {
              this.disconnecting = false;
              this.snackBar.open(this.t('marketing.messages.disconnected'), this.closeLabel, { duration: 3000 });
              this.router.navigate(['/marketplaces']);
            },
            error: (err) => {
              this.disconnecting = false;
              console.error('Disconnect error:', err);
              this.snackBar.open(this.t('marketing.messages.disconnectFailed'), this.closeLabel, { duration: 5000 });
            }
          });
        },
        error: () => {
          this.disconnecting = false;
          this.snackBar.open(this.t('marketing.messages.credentialLookupFailed'), this.closeLabel, { duration: 3000 });
        }
      });
    });
  }
}
