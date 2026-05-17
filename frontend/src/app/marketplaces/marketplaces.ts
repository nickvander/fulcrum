import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { environment } from '../../environments/environment';

export interface Marketplace {
  id: number;
  name: string;
  api_base_url?: string;
}

export interface MarketplaceListing {
  id: number;
  product_id: number;
  marketplace_id: number;
  external_listing_id?: string;
  listing_url?: string;
  status?: string;
  sync_status?: string;
  last_sync?: string;
  marketplace_price?: number;
  metadata_json?: MarketplaceListingMetadata;
}

/**
 * Marketplace-agnostic structure for listing content.
 * Fields are designed to map to Amazon, MercadoLibre, and eBay APIs.
 */
export interface MarketplaceListingMetadata {
  // Universal fields
  title: string;
  description: string;
  keywords?: string[];

  // Price and quantity (universal)
  price?: number;
  currency?: string;
  quantity?: number;
  condition?: 'new' | 'used' | 'refurbished';

  // Category (platform-specific IDs stored here)
  category_id?: string;

  // Amazon-specific
  amazon?: {
    product_type?: string;
    bullet_points?: string[];
    search_terms?: string[];
    sku?: string;
  };

  // MercadoLibre-specific
  mercadolibre?: {
    site_id?: string;
    listing_type_id?: string;
    catalog_product_id?: string;
  };

  // eBay-specific
  ebay?: {
    item_specifics?: Record<string, string>;
    subtitle?: string;
    listing_duration?: string;
  };
}

export interface MarketplaceListingCreate {
  product_id: number;
  marketplace_id: number;
  status?: string;
  sync_status?: string;
  marketplace_price?: number;
  metadata_json?: MarketplaceListingMetadata;
}

@Injectable({
  providedIn: 'root',
})
export class MarketplacesService {
  private apiUrl = `${environment.apiUrl}/marketplace`;

  constructor(private http: HttpClient) { }

  getMarketplaces(): Observable<Marketplace[]> {
    return this.http.get<Marketplace[]>(`${this.apiUrl}/`);
  }

  getMarketplaceByName(name: string): Observable<Marketplace | undefined> {
    return this.getMarketplaces().pipe(
      map(marketplaces => marketplaces.find(
        m => m.name.toLowerCase() === name.toLowerCase()
      ))
    );
  }

  getMarketplaceListings(): Observable<MarketplaceListing[]> {
    return this.http.get<MarketplaceListing[]>(`${this.apiUrl}/listings/`);
  }

  createListing(listing: MarketplaceListingCreate): Observable<MarketplaceListing> {
    return this.http.post<MarketplaceListing>(`${this.apiUrl}/listings/`, listing);
  }

  syncListing(listingId: number): Observable<MarketplaceListing> {
    return this.http.post<MarketplaceListing>(`${this.apiUrl}/listings/${listingId}/sync`, {});
  }

  // OAuth methods
  getAuthUrl(marketplaceName: string): Observable<{ auth_url: string; marketplace_id: number }> {
    // Use the by-name endpoint which auto-creates the marketplace if needed
    return this.http.get<{ auth_url: string; marketplace_id: number }>(
      `${environment.apiUrl}/marketplace-credentials/by-name/${marketplaceName.toLowerCase()}/authorize`
    );
  }

  importListings(marketplaceId: number): Observable<{ synced: number; created_product_shell: number; orphaned: number }> {
    return this.http.post<{ synced: number; created_product_shell: number; orphaned: number }>(`${this.apiUrl}/import`, null, {
      params: { marketplace_id: marketplaceId.toString() }
    });
  }

  createMarketplace(marketplace: { name: string; api_base_url: string }): Observable<Marketplace> {
    return this.http.post<Marketplace>(`${this.apiUrl}/`, marketplace);
  }

  getCredentialForMarketplace(marketplaceId: number): Observable<MarketplaceCredential | null> {
    return this.http
      .get<MarketplaceCredential>(`${environment.apiUrl}/marketplace-credentials/${marketplaceId}`)
      .pipe(catchError(() => of(null)));
  }

  disconnectCredential(credentialId: number): Observable<unknown> {
    return this.http.delete(`${environment.apiUrl}/marketplace-credentials/${credentialId}`);
  }

  getMarketplaceSummary(marketplaceId: number): Observable<MarketplaceSummary> {
    return this.http.get<MarketplaceSummary>(`${this.apiUrl}/${marketplaceId}/summary`);
  }
}

export interface MarketplaceCredential {
  id: number;
  marketplace_id: number;
  user_id: number;
  token_type?: string;
  scopes?: string;
  expires_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface MarketplaceSummary {
  marketplace_id: number;
  listing_count: number;
  healthy_count: number;
  issues_count: number;
  last_sync_at?: string | null;
  credential_connected: boolean;
  token_expires_at?: string | null;
  token_expires_in_days?: number | null;
  /**
   * True when the most recent refresh attempt failed and the credential
   * was marked by `_mark_reauth_required` (e.g. invalid_grant, revoked
   * refresh token). Renders the reauth chip on the marketplace card.
   */
  needs_reauthorization?: boolean;
  /**
   * Human-readable reason from `last_refresh_error`, shown as the
   * tooltip on the reauth chip. Empty when `needs_reauthorization` is
   * false.
   */
  reauthorization_reason?: string | null;
}
