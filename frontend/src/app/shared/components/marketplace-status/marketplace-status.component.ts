import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatIconModule } from '@angular/material/icon';
import { MarketplaceListing } from '../../../products/models/product.model';

@Component({
    selector: 'app-marketplace-status',
    standalone: true,
    imports: [CommonModule, MatTooltipModule, MatIconModule],
    template: `
    <div class="status-container" *ngIf="listings && listings.length > 0">
      <div *ngFor="let listing of listings" class="marketplace-badge" 
           [matTooltip]="getTooltip(listing)"
           [class.status-active]="listing.status === 'active'"
           [class.status-error]="listing.status === 'error'"
           [class.status-pending]="listing.status === 'pending'">
        <span class="marketplace-icon">{{ getMarketplaceIcon(listing.marketplace_id) }}</span>
        <span class="status-dot"></span>
      </div>
    </div>
    <span *ngIf="!listings || listings.length === 0" class="no-listings">-</span>
  `,
    styles: [`
    .status-container {
      display: flex;
      gap: 4px;
    }
    .marketplace-badge {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      border-radius: 4px;
      background-color: #f5f5f5;
      position: relative;
      cursor: help;
      border: 1px solid #e0e0e0;
    }
    .marketplace-icon {
      font-size: 10px;
      font-weight: bold;
      color: #555;
    }
    .status-dot {
      position: absolute;
      bottom: -2px;
      right: -2px;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: #9e9e9e; /* Default */
      border: 1px solid white;
    }
    .status-active {
      border-color: #a5d6a7;
      background-color: #e8f5e9;
      .status-dot { background-color: #4caf50; }
    }
    .status-error {
      border-color: #ef9a9a;
      background-color: #ffebee;
      .status-dot { background-color: #f44336; }
    }
    .status-pending {
      border-color: #ffcc80;
      background-color: #fff3e0;
      .status-dot { background-color: #ff9800; }
    }
    .no-listings {
      color: #ccc;
      font-size: 0.8rem;
    }
  `]
})
export class MarketplaceStatusComponent {
    @Input() listings: MarketplaceListing[] = [];

    getMarketplaceIcon(id: number): string {
        // Simple mapping for now
        switch (id) {
            case 1: return 'AMZ'; // Amazon
            case 2: return 'EBY'; // eBay
            case 3: return 'SHO'; // Shopify
            case 4: return 'ML';  // MercadoLibre
            default: return 'MK' + id;
        }
    }

    getTooltip(listing: MarketplaceListing): string {
        const marketplaceName = this.getMarketplaceName(listing.marketplace_id);
        return `${marketplaceName}: ${listing.status || 'Unknown'}`;
    }

    getMarketplaceName(id: number): string {
        switch (id) {
            case 1: return 'Amazon';
            case 2: return 'eBay';
            case 3: return 'Shopify';
            case 4: return 'MercadoLibre';
            default: return 'Marketplace ' + id;
        }
    }
}
