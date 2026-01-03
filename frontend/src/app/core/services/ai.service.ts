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
}
