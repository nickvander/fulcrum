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
}
