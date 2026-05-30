import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, shareReplay } from 'rxjs/operators';
import { environment } from '../../environments/environment';

/**
 * One supported (or planned) marketplace, as declared by the backend
 * catalog (`GET /marketplace/catalog`). The frontend reads this instead
 * of hardcoding the channel list, so adding a marketplace server-side
 * automatically surfaces it across the channels page, add-channel
 * dialog, and listing-type dropdown.
 */
export interface MarketplaceCatalogEntry {
  key: string;
  display_name: string;
  status: 'live' | 'beta' | 'planned';
  supports_oauth: boolean;
  is_primary: boolean;
  is_connectable: boolean;
  recommended_region: string | null;
  brand_color: string;
}

@Injectable({ providedIn: 'root' })
export class MarketplaceCatalogService {
  private readonly apiUrl = `${environment.apiUrl}/marketplace`;
  private cache$?: Observable<MarketplaceCatalogEntry[]>;

  constructor(private http: HttpClient) {}

  /**
   * The marketplace catalog, in backend-defined priority order
   * (MercadoLibre first). Cached + shared so multiple consumers on a
   * page don't each refetch. Falls back to an empty list on error so a
   * catalog hiccup degrades gracefully rather than blanking the page.
   */
  getCatalog(): Observable<MarketplaceCatalogEntry[]> {
    if (!this.cache$) {
      this.cache$ = this.http
        .get<MarketplaceCatalogEntry[]>(`${this.apiUrl}/catalog`)
        .pipe(
          catchError(() => of([] as MarketplaceCatalogEntry[])),
          shareReplay(1),
        );
    }
    return this.cache$;
  }

  /** Convention-based logo path. Live channels ship a PNG under this
   *  path; planned channels (no logo yet) fall back to an icon in the
   *  template. */
  logoFor(key: string): string {
    return `images/marketplaces/${key}.png`;
  }
}
