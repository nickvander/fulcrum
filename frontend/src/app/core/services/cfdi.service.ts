import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

/** The seller's CFDI issuer (emisor) tax identity. */
export interface CfdiIssuerConfig {
  rfc: string | null;
  name: string | null;
  tax_regime: string | null;
  postal_code: string | null;
  default_product_key: string;
  default_unit_key: string;
  cfdi_use: string;
  iva_rate: number;
  is_configured: boolean;
}

export interface CfdiIssuerConfigUpdate {
  rfc?: string | null;
  name?: string | null;
  tax_regime?: string | null;
  postal_code?: string | null;
  default_product_key?: string | null;
  default_unit_key?: string | null;
  cfdi_use?: string | null;
  iva_rate?: number | null;
}

export interface CfdiConcept {
  description: string;
  product_key: string;
  unit_key: string;
  quantity: number;
  unit_price: number;
  amount: number;
  iva_amount: number;
}

export interface CfdiOrderRow {
  order_id: number;
  external_order_id: string | null;
  issued_at: string;
  source: string | null;
  currency: string;
  receiver_rfc: string;
  receiver_name: string;
  cfdi_use: string;
  concepts: CfdiConcept[];
  subtotal: number;
  iva_amount: number;
  total: number;
}

export interface CfdiReport {
  rows: CfdiOrderRow[];
  issuer: CfdiIssuerConfig;
  start_date: string | null;
  end_date: string | null;
  order_count: number;
  subtotal: number;
  iva_amount: number;
  total: number;
}

export interface CfdiDateRange {
  startDate?: string | null;
  endDate?: string | null;
}

/**
 * Talks to the CFDI export API (`/reports/cfdi`) and the issuer config
 * (`/settings/cfdi`). Export-only: emits realized sales in a CFDI-ready
 * shape for an accountant / PAC to timbrar. v1 issues every order to the
 * RFC genérico ("público en general").
 */
@Injectable({ providedIn: 'root' })
export class CfdiService {
  private reportsUrl = `${environment.apiUrl}/reports`;
  private settingsUrl = `${environment.apiUrl}/settings`;

  constructor(private http: HttpClient) {}

  getConfig(): Observable<CfdiIssuerConfig> {
    return this.http.get<CfdiIssuerConfig>(`${this.settingsUrl}/cfdi`);
  }

  saveConfig(update: CfdiIssuerConfigUpdate): Observable<CfdiIssuerConfig> {
    return this.http.post<CfdiIssuerConfig>(`${this.settingsUrl}/cfdi`, update);
  }

  report(range?: CfdiDateRange): Observable<CfdiReport> {
    return this.http.get<CfdiReport>(`${this.reportsUrl}/cfdi`, {
      params: this.rangeParams(range),
    });
  }

  exportCsv(range?: CfdiDateRange): Observable<Blob> {
    return this.http.get(`${this.reportsUrl}/cfdi/export`, {
      params: this.rangeParams(range),
      responseType: 'blob',
    });
  }

  private rangeParams(range?: CfdiDateRange): HttpParams {
    let params = new HttpParams();
    if (range?.startDate) params = params.set('start_date', range.startDate);
    if (range?.endDate) params = params.set('end_date', range.endDate);
    return params;
  }
}
