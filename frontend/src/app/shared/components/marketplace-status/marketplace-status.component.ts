import { Component, Input } from '@angular/core';

import { MatTooltipModule } from '@angular/material/tooltip';
import { MatIconModule } from '@angular/material/icon';
import { MarketplaceListing } from '../../../products/models/product.model';

@Component({
  selector: 'app-marketplace-status',
  standalone: true,
  imports: [MatTooltipModule, MatIconModule],
  template: `
    @if (listings && listings.length > 0) {
      <div class="status-container">
        @for (listing of listings; track listing.id) {
          <div class="marketplace-badge"
            [matTooltip]="getTooltip(listing)"
            [class.status-active]="listing.status === 'active'"
            [class.status-error]="listing.status === 'error'"
            [class.status-pending]="listing.status === 'pending'">
            @if (getMarketplaceLogo(listing.marketplace_id)) {
                <img [src]="getMarketplaceLogo(listing.marketplace_id)" class="mp-logo" alt="logo">
            } @else {
                <span class="marketplace-icon">{{ getMarketplaceIcon(listing.marketplace_id) }}</span>
            }
            <span class="status-dot"></span>
          </div>
        }
      </div>
    }
    @if (!listings || listings.length === 0) {
      <span class="no-listings">-</span>
    }
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
      width: 28px;
      height: 28px;
      border-radius: 6px;
      background-color: white;
      position: relative;
      cursor: help;
      border: 1px solid #e0e0e0;
      overflow: hidden;
      box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .mp-logo {
      width: 20px;
      height: 20px;
      object-fit: contain;
    }
    .marketplace-icon {
      font-size: 10px;
      font-weight: bold;
      color: #555;
    }
    .status-dot {
      position: absolute;
      bottom: 0px;
      right: 0px;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: #9e9e9e; /* Default */
      border: 1.5px solid white;
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

  getMarketplaceLogo(id: number): string | null {
    switch (id) {
      case 1: return 'assets/images/marketplaces/amazon.png';
      case 4: return 'assets/images/marketplaces/mercadolibre.png';
      default: return null;
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
