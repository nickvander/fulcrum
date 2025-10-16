import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ProductTemplate, CustomFieldTemplate } from '../models/product-template.model';
import { NotificationService } from '../../core/services/notification.service';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ProductTemplateService {
  private apiUrl = `${environment.apiUrl}/product-templates`;

  constructor(
    private http: HttpClient,
    private notificationService: NotificationService
  ) {}

  getProductTemplates(): Observable<ProductTemplate[]> {
    return this.http.get<ProductTemplate[]>(`${this.apiUrl}/`);
  }

  getProductTemplateById(id: number): Observable<ProductTemplate> {
    return this.http.get<ProductTemplate>(`${this.apiUrl}/${id}`);
  }

  createProductTemplate(template: Omit<ProductTemplate, 'id'>): Observable<ProductTemplate> {
    return this.http.post<ProductTemplate>(`${this.apiUrl}/`, template).pipe(
      // tap(() => this.notificationService.showSuccess('Product template created successfully!'))
    );
  }

  updateProductTemplate(template: ProductTemplate): Observable<ProductTemplate> {
    return this.http.put<ProductTemplate>(`${this.apiUrl}/${template.id}`, template).pipe(
      // tap(() => this.notificationService.showSuccess('Product template updated successfully!'))
    );
  }

  deleteProductTemplate(id: number): Observable<unknown> {
    return this.http.delete(`${this.apiUrl}/${id}`).pipe(
      // tap(() => this.notificationService.showSuccess('Product template deleted successfully!'))
    );
  }

  // Custom Field Template Methods
  getCustomFieldTemplates(templateId: number): Observable<CustomFieldTemplate[]> {
    return this.http.get<CustomFieldTemplate[]>(`${this.apiUrl}/${templateId}/custom-fields`);
  }

  createCustomFieldTemplate(templateId: number, field: Omit<CustomFieldTemplate, 'id'>): Observable<CustomFieldTemplate> {
    return this.http.post<CustomFieldTemplate>(`${this.apiUrl}/${templateId}/custom-fields`, field);
  }

  updateCustomFieldTemplate(templateId: number, fieldId: number, field: Partial<CustomFieldTemplate>): Observable<CustomFieldTemplate> {
    return this.http.put<CustomFieldTemplate>(`${this.apiUrl}/${templateId}/custom-fields/${fieldId}`, field);
  }

  deleteCustomFieldTemplate(templateId: number, fieldId: number): Observable<CustomFieldTemplate> {
    return this.http.delete<CustomFieldTemplate>(`${this.apiUrl}/${templateId}/custom-fields/${fieldId}`);
  }

  // Create product from template
  createProductFromTemplate(templateId: number, productData: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/${templateId}/create-product`, productData);
  }
}