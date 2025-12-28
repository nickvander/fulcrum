import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
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

  getMarketplaceListings(): Observable<MarketplaceListing[]> {
    return this.http.get<MarketplaceListing[]>(`${this.apiUrl}/listings/`);
  }

  createListing(listing: any): Observable<MarketplaceListing> {
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
}
