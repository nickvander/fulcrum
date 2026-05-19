import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, of, shareReplay, tap } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface AiCapabilities {
    ready: boolean;
    enabled: boolean;
    configured: boolean;
    provider: string | null;
}

const DISABLED_CAPABILITIES: AiCapabilities = {
    ready: false,
    enabled: false,
    configured: false,
    provider: null,
};

export interface ProductIdentificationResponse {
    name: string;
    brand?: string;
    sku?: string;
    description?: string;
    category?: string;
    error?: string;
    exists?: boolean;
    product_id?: number | string;
    message?: string;
}

export interface DescriptionGenerationRequest {
    product_name: string;
    context?: string;
    tone?: string;
    length?: string;
}

export interface DescriptionGenerationResponse {
    description?: string;
    seo_keywords?: string[];
    tone_used?: string;
    error?: string;
}

export interface ListingDescriptionRequest {
    product_id: number;
    marketplace_name: string;
    include_title?: boolean;
    include_keywords?: boolean;
}

export interface ListingDescriptionResponse {
    title?: string;
    description?: string;
    keywords?: string[];
    marketplace: string;
    error?: string;
}

@Injectable({
    providedIn: 'root'
})
export class AiService {
    private apiUrl = `${environment.apiUrl}/ai`;

    private readonly _capabilities = new BehaviorSubject<AiCapabilities>(DISABLED_CAPABILITIES);
    readonly capabilities$ = this._capabilities.asObservable();
    private capabilitiesRequest$?: Observable<AiCapabilities>;

    constructor(private http: HttpClient) { }

    /**
     * Fetch (and cache) the AI readiness signal. UI components should call
     * this in ngOnInit and gate AI buttons on `capabilities$ | async` so the
     * button never appears when the backend would refuse it.
     */
    getCapabilities(forceRefresh = false): Observable<AiCapabilities> {
        if (!forceRefresh && this.capabilitiesRequest$) {
            return this.capabilitiesRequest$;
        }
        this.capabilitiesRequest$ = this.http
            .get<AiCapabilities>(`${this.apiUrl}/capabilities`)
            .pipe(
                catchError(() => of(DISABLED_CAPABILITIES)),
                tap(caps => this._capabilities.next(caps)),
                shareReplay(1),
            );
        return this.capabilitiesRequest$;
    }

    /** Stream of just the `ready` boolean — most consumers only want this. */
    isReady$(): Observable<boolean> {
        return this.getCapabilities().pipe(map(c => c.ready));
    }

    /** Drop the cached capabilities — call after a settings update so the
     * very next AI button check re-reads the backend. */
    invalidateCapabilities(): void {
        this.capabilitiesRequest$ = undefined;
        this._capabilities.next(DISABLED_CAPABILITIES);
    }

    identifyProduct(imageFile: File): Observable<ProductIdentificationResponse> {
        const formData = new FormData();
        formData.append('file', imageFile);

        return this.http.post<ProductIdentificationResponse>(`${this.apiUrl}/identify-product`, formData);
    }

    generateDescription(request: DescriptionGenerationRequest): Observable<DescriptionGenerationResponse> {
        return this.http.post<DescriptionGenerationResponse>(`${this.apiUrl}/generate-description`, request);
    }

    generateListingDescription(request: ListingDescriptionRequest): Observable<ListingDescriptionResponse> {
        return this.http.post<ListingDescriptionResponse>(`${this.apiUrl}/generate-listing-description`, request);
    }
}
