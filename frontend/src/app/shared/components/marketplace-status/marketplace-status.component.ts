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

  getMarketplaceLogo(listing: MarketplaceListing): string | null {
    if (!listing) return null;
    const url = listing.listing_url || '';
    if (url.includes('amazon')) return 'assets/images/marketplaces/amazon.png';
    if (url.includes('mercadolibre.com')) return 'assets/images/marketplaces/mercadolibre.png';
    switch (listing.marketplace_id) {
      case 1: return 'assets/images/marketplaces/mercadolibre.png';
      case 2: return 'assets/images/marketplaces/amazon.png';
      default: return null;
    }
  }

  getFallbackLabel(listing: MarketplaceListing): string {
    if (!listing) return 'Mk';
    const url = listing.listing_url || '';
    if (url.includes('amazon')) return 'AMZ';
    if (url.includes('mercadolibre.com')) return 'ML';
    switch (listing.marketplace_id) {
      case 1: return 'ML';
      case 2: return 'AMZ';
      case 3: return 'Shp';
      default: return 'Mk';
    }
  }

  getTooltip(listing: MarketplaceListing): string {
    const marketplaceName = this.getMarketplaceName(listing);
    return `${marketplaceName}: ${listing.status || 'Unknown'}`;
  }

  getMarketplaceName(listing: MarketplaceListing): string {
    if (!listing) return 'Marketplace';
    const url = listing.listing_url || '';
    if (url.includes('amazon')) return 'Amazon';
    if (url.includes('mercadolibre.com')) return 'MercadoLibre';
    switch (listing.marketplace_id) {
      case 1: return 'MercadoLibre';
      case 2: return 'Amazon';
      case 3: return 'Shopify';
      default: return 'Marketplace ' + listing.marketplace_id;
    }
  }

  // Get unique listings (one per marketplace_id)
  getUniqueListings(): MarketplaceListing[] {
    if (!this.listings) return [];
    const seen = new Set<number>();
    return this.listings.filter(listing => {
      if (seen.has(listing.marketplace_id)) {
        return false;
      }
      seen.add(listing.marketplace_id);
      return true;
    });
  }
}
