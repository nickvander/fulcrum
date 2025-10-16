import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Product } from '../models/product.model';
import { NotificationService } from '../../core/services/notification.service';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class BatchOperationsService {
  private apiUrl = `${environment.apiUrl}/products`;

  constructor(
    private http: HttpClient,
    private notificationService: NotificationService
  ) {}

  // Batch price updates
  batchUpdatePrices(productIds: number[], priceAdjustment: number, adjustmentType: 'set' | 'increase' = 'set'): Observable<any> {
    const payload = {
      product_ids: productIds,
      price_adjustment: priceAdjustment,
      adjustment_type: adjustmentType
    };
    
    return this.http.post<any>(`${this.apiUrl}/batch-update-prices`, payload).pipe(
      // tap(() => this.notificationService.showSuccess(`${productIds.length} products updated successfully!`))
    );
  }

  // Batch category assignments
  batchUpdateCategories(productIds: number[], categoryId: string): Observable<any> {
    const payload = {
      product_ids: productIds,
      category: categoryId
    };
    
    return this.http.post<any>(`${this.apiUrl}/batch-update-categories`, payload).pipe(
      // tap(() => this.notificationService.showSuccess(`${productIds.length} products updated successfully!`))
    );
  }

  // Batch custom field updates
  batchUpdateCustomFields(productIds: number[], customFieldUpdates: { [key: string]: any }): Observable<any> {
    const payload = {
      product_ids: productIds,
      custom_field_updates: customFieldUpdates
    };
    
    return this.http.post<any>(`${this.apiUrl}/batch-update-custom-fields`, payload).pipe(
      // tap(() => this.notificationService.showSuccess(`${productIds.length} products updated successfully!`))
    );
  }

  // Batch image upload for multiple products
  batchUploadImages(formData: FormData): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/batch-upload-images`, formData).pipe(
      // tap(() => this.notificationService.showSuccess('Images uploaded successfully!'))
    );
  }

  // Delete multiple products
  deleteMultipleProducts(productIds: number[]): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/`, {
      body: { ids: productIds }
    }).pipe(
      // tap(() => this.notificationService.showSuccess(`${productIds.length} products deleted successfully!`))
    );
  }
}