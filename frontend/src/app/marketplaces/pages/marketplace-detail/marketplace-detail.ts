import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import {
  Marketplace,
  MarketplacesService,
  MarketplaceListing,
  MarketplaceFeeConfigRecomputeResult,
} from '../../marketplaces';
import { Observable, finalize, of } from 'rxjs';
import { ConfirmationDialog } from '../../../shared/components/confirmation-dialog/confirmation-dialog';

@Component({
  selector: 'app-marketplace-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatTableModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatChipsModule,
    MatProgressSpinnerModule,
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

  // Phase 8 fee-config form state. Kept inline on the detail page
  // rather than a separate route — operators tend to update fees
  // and recompute breakdowns together in the same flow, so the
  // card stays nearby.
  marketplace: Marketplace | null = null;
  feeRatePercent = 0;       // operator-visible form value, in PERCENT
                            // (e.g. 16 for 16%). Converted to fraction
                            // before sending so the API/DB stays in
                            // the same shape as
                            // `Marketplace.default_fee_rate`.
  shippingCost = 0;
  savingFeeConfig = false;
  recomputing = false;
  recomputeResult: MarketplaceFeeConfigRecomputeResult | null = null;

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
    if (this.marketplaceId) {
      this.loadMarketplace(parseInt(this.marketplaceId, 10));
    }
  }

  private loadMarketplace(id: number): void {
    this.marketplaceService.getMarketplaceById(id).subscribe({
      next: (mp) => {
        this.marketplace = mp;
        // Convert the API's fraction → percent for the form.
        this.feeRatePercent = Math.round((mp.default_fee_rate ?? 0) * 10000) / 100;
        this.shippingCost = mp.default_shipping_cost ?? 0;
      },
      error: () => {
        // Non-fatal — the listings + actions still work without the
        // marketplace row. The fee-config card just stays hidden.
      },
    });
  }

  saveFeeConfig(): void {
    if (!this.marketplace || this.savingFeeConfig) return;
    if (this.feeRatePercent < 0 || this.shippingCost < 0) {
      this.snackBar.open(
        this.t('marketing.feeConfig.errorNegative'),
        this.closeLabel, { duration: 4000 },
      );
      return;
    }
    this.savingFeeConfig = true;
    const update = {
      default_fee_rate: this.feeRatePercent / 100,
      default_shipping_cost: this.shippingCost,
    };
    this.marketplaceService.updateFeeConfig(this.marketplace.id, update)
      .pipe(finalize(() => (this.savingFeeConfig = false)))
      .subscribe({
        next: (mp) => {
          this.marketplace = mp;
          this.snackBar.open(
            this.t('marketing.feeConfig.saved'),
            this.closeLabel, { duration: 3000 },
          );
        },
        error: () => {
          // HttpErrorInterceptor surfaces the localized error from
          // the backend (apiErrors.marketplace.feeRateNegative etc.).
        },
      });
  }

  recomputeBreakdowns(): void {
    if (!this.marketplace || this.recomputing) return;
    this.recomputing = true;
    this.recomputeResult = null;
    this.marketplaceService.recomputeCostBreakdowns(this.marketplace.id)
      .pipe(finalize(() => (this.recomputing = false)))
      .subscribe({
        next: (result) => {
          this.recomputeResult = result;
          const summary = this.t('marketing.feeConfig.recomputeSummary', {
            created: result.breakdowns_created,
            updated: result.breakdowns_updated,
            errors: result.errors,
          });
          this.snackBar.open(summary, this.closeLabel, { duration: 5000 });
        },
        error: () => {
          this.snackBar.open(
            this.t('marketing.feeConfig.recomputeFailed'),
            this.closeLabel, { duration: 4000 },
          );
        },
      });
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
