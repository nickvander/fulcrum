import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface AuditLog {
  id: number;
  user_id: number;
  action_performed_by: number;
  action: string;
  details: string;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
  user?: {
    email: string;
    first_name?: string;
    last_name?: string;
  };
  actor?: {
    email: string;
    first_name?: string;
    last_name?: string;
  };
}

@Injectable({
  providedIn: 'root'
})
export class AuditLogService {
  private apiUrl = `${environment.apiUrl}/audit-logs`;

  constructor(private http: HttpClient) { }

  getAuditLogs(
    page: number = 0,
    limit: number = 20,
    filters: {
      userId?: number,
      action?: string,
      startDate?: string,
      endDate?: string
    } = {}
  ): Observable<AuditLog[]> {
    let params = new HttpParams()
      .set('skip', (page * limit).toString())
      .set('limit', limit.toString());

    if (filters.userId) {
      params = params.set('user_id', filters.userId.toString());
    }
    if (filters.action) {
      params = params.set('action', filters.action);
    }
    if (filters.startDate) {
      params = params.set('start_date', filters.startDate);
    }
    if (filters.endDate) {
      params = params.set('end_date', filters.endDate);
    }

    return this.http.get<AuditLog[]>(this.apiUrl, { params });
  }
}
