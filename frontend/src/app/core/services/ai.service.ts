import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

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

@Injectable({
    providedIn: 'root'
})
export class AiService {
    private apiUrl = `${environment.apiUrl}/ai`;

    constructor(private http: HttpClient) { }

    identifyProduct(imageFile: File): Observable<ProductIdentificationResponse> {
        const formData = new FormData();
        formData.append('file', imageFile);

        return this.http.post<ProductIdentificationResponse>(`${this.apiUrl}/identify-product`, formData);
    }

    generateDescription(request: DescriptionGenerationRequest): Observable<DescriptionGenerationResponse> {
        return this.http.post<DescriptionGenerationResponse>(`${this.apiUrl}/generate-description`, request);
    }
}
