import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';

export interface CatalogImportItem {
  sku: string | null;
  name: string;
  description: string | null;
  cost_price: number | null;
  default_resale_price: number | null;
  category: string | null;
  brand: string | null;
  supplier_sku: string | null;
  raw: { [k: string]: string };
  warnings: string[];
  selected: boolean;
}

export interface CatalogImportReview {
  id: number;
  file_name: string;
  content_type: string | null;
  source: string;
  status: 'pending' | 'approved' | 'rejected';
  supplier_id: number | null;
  extracted_data: { items: CatalogImportItem[]; vendor_name?: string; auto_linked_supplier_name?: string | null };
  warnings: string[];
  created_at: string;
  reviewed_at: string | null;
  detected_vendor_name?: string | null;
  auto_linked_supplier_name?: string | null;
}

export interface CatalogImportApproveResponse {
  import_review: CatalogImportReview;
  created_product_ids: number[];
  skipped_count: number;
  skipped_reasons: string[];
}

export interface CatalogImportCapabilities {
  csv: boolean;
  ai: boolean;
  ai_enabled: boolean;
  ai_configured: boolean;
  ai_provider: string | null;
  accepted_extensions: string[];
}

export interface ImportTemplate {
  id: number;
  name: string;
  source_type: string;
  column_map: { [sourceHeader: string]: string };
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ImportTemplatePreview {
  headers: string[];
  sample_rows: { [k: string]: string }[];
  detected_field_map: { [canonicalField: string]: string };
}

@Injectable({ providedIn: 'root' })
export class CatalogImportService {
  private readonly apiUrl = `${environment.apiUrl}/catalog-imports`;

  constructor(private http: HttpClient) {}

  capabilities(): Observable<CatalogImportCapabilities> {
    return this.http.get<CatalogImportCapabilities>(`${this.apiUrl}/capabilities`);
  }

  upload(
    file: File,
    supplierId?: number | null,
    templateId?: number | null,
  ): Observable<CatalogImportReview> {
    const formData = new FormData();
    formData.append('file', file);
    let params = new HttpParams();
    if (supplierId != null) {
      params = params.set('supplier_id', String(supplierId));
    }
    if (templateId != null) {
      params = params.set('template_id', String(templateId));
    }
    return this.http.post<CatalogImportReview>(`${this.apiUrl}/reviews`, formData, { params });
  }

  // --- Named import templates ----------------------------------------------

  previewForMapping(file: File): Observable<ImportTemplatePreview> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ImportTemplatePreview>(
      `${this.apiUrl}/templates/preview`, formData,
    );
  }

  listTemplates(): Observable<ImportTemplate[]> {
    return this.http.get<ImportTemplate[]>(`${this.apiUrl}/templates`);
  }

  createTemplate(payload: { name: string; column_map: { [k: string]: string }; notes?: string }): Observable<ImportTemplate> {
    return this.http.post<ImportTemplate>(`${this.apiUrl}/templates`, payload);
  }

  deleteTemplate(id: number): Observable<ImportTemplate> {
    return this.http.delete<ImportTemplate>(`${this.apiUrl}/templates/${id}`);
  }

  approve(
    reviewId: number,
    items: CatalogImportItem[],
    supplierId?: number | null,
  ): Observable<CatalogImportApproveResponse> {
    return this.http.post<CatalogImportApproveResponse>(
      `${this.apiUrl}/reviews/${reviewId}/approve`,
      { supplier_id: supplierId ?? null, items },
    );
  }

  reject(reviewId: number): Observable<CatalogImportReview> {
    return this.http.post<CatalogImportReview>(`${this.apiUrl}/reviews/${reviewId}/reject`, {});
  }
}
