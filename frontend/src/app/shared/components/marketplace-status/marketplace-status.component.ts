import { Component, Input } from '@angular/core';

import { MatTooltipModule } from '@angular/material/tooltip';
import { MatIconModule } from '@angular/material/icon';
import { MarketplaceListing } from '../../../products/models/product.model';

@Component({
  selector: 'app-marketplace-status',
  standalone: true,
  imports: [MatTooltipModule, MatIconModule],
  templateUrl: './marketplace-status.component.html',
  styleUrls: ['./marketplace-status.component.scss']
})
export class MarketplaceStatusComponent {
  @Input() listings: MarketplaceListing[] = [];
  @Input() simple = false;

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
      // User requested "AMZ" badge instead of logo for better visibility
      case 1: return null;
      case 4: return 'assets/images/marketplaces/mercadolibre.png';
      default: return null;
    }
  }

  getFallbackLabel(id: number): string {
    switch (id) {
      case 1: return 'AMZ';
      case 2: return 'eBay';
      case 3: return 'Shp';
      case 4: return 'ML';
      default: return 'Mk';
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
