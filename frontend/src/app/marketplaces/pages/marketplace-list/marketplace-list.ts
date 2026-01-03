import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule } from '@ngneat/transloco';
import { MarketplacesService, Marketplace } from '../../marketplaces';
import { Observable, of } from 'rxjs';

@Component({
  selector: 'app-marketplace-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatDividerModule,
    MatSnackBarModule,
    MatTooltipModule,
    TranslocoModule
  ],
  templateUrl: './marketplace-list.html',
  styleUrl: './marketplace-list.scss',
})
export class MarketplaceListComponent implements OnInit {
  marketplaces$: Observable<Marketplace[]> = of([]);
  syncing = false;
  showAddDialog = false;

  constructor(
    private marketplaceService: MarketplacesService,
    private snackBar: MatSnackBar
  ) { }

  ngOnInit(): void {
    this.marketplaces$ = this.marketplaceService.getMarketplaces();
  }

  syncMarketplace(marketplaceId: number): void {
    this.syncing = true;
    this.marketplaceService.importListings(marketplaceId).subscribe({
      next: (stats) => {
        this.syncing = false;
        const msg = `Sync complete! Synced: ${stats.synced}, Created: ${stats.created_product_shell}`;
        this.snackBar.open(msg, 'Close', { duration: 5000 });
        this.marketplaces$ = this.marketplaceService.getMarketplaces();
      },
      error: (err) => {
        this.syncing = false;
        console.error('Sync error:', err);
        this.snackBar.open('Sync failed. Check your credentials.', 'Close', { duration: 5000 });
      }
    });
  }

  getMarketplaceLogo(name: string): string {
    const n = name.toLowerCase();
    if (n.includes('amazon')) return 'images/marketplaces/amazon.png';
    if (n.includes('mercado')) return 'images/marketplaces/mercadolibre.png';
    return 'images/marketplaces/default.png';
  }
}
