import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export type PaymentStatus =
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'refunded'
  | 'cancelled';

export interface Payment {
  id: number;
  sales_order_id: number | null;
  user_id: number | null;
  provider: string;
  external_payment_id: string | null;
  status: PaymentStatus | string;
  amount: number;
  currency: string;
  payer_email: string | null;
  raw_response: Record<string, unknown> | null;
  last_webhook_payload: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PaymentListResponse {
  items: Payment[];
  total: number;
}

export interface PaymentListParams {
  status?: PaymentStatus | null;
  provider?: string | null;
  skip?: number;
  limit?: number;
}

/**
 * Thin HTTP wrapper around the backend `/api/v1/payments` surface
 * shipped in commit 7a3dabb. Pairs with `PaymentsPageComponent` which
 * owns the list + status filter + detail dialog. There is no
 * create/update from the admin UI — payments are created via
 * `POST /payments/` from the storefront checkout, and status is
 * driven by the MP webhook.
 */
@Injectable({ providedIn: 'root' })
export class PaymentsService {
  private apiUrl = `${environment.apiUrl}/payments`;

  constructor(private http: HttpClient) {}

  list(params: PaymentListParams = {}): Observable<PaymentListResponse> {
    let httpParams = new HttpParams();
    if (params.status) httpParams = httpParams.set('status', params.status);
    if (params.provider) httpParams = httpParams.set('provider', params.provider);
    if (params.skip != null) httpParams = httpParams.set('skip', String(params.skip));
    if (params.limit != null) httpParams = httpParams.set('limit', String(params.limit));
    return this.http.get<PaymentListResponse>(`${this.apiUrl}/`, { params: httpParams });
  }

  get(id: number): Observable<Payment> {
    return this.http.get<Payment>(`${this.apiUrl}/${id}`);
  }
}
