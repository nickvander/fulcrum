import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { UserAuditLog } from '../models/audit-log.model';
import { environment } from '../../../environments/environment';

export interface AuditLogListParams {
  skip?: number;
  limit?: number;
  user_id?: number;
  action?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuditLogService {
  private apiUrl = `${environment.apiUrl}/audit-logs`;

  constructor(private http: HttpClient) {}

  getAuditLogs(params?: AuditLogListParams): Observable<UserAuditLog[]> {
    let httpParams = new HttpParams();
    
    if (params) {
      if (params.skip !== undefined) httpParams = httpParams.set('skip', params.skip.toString());
      if (params.limit !== undefined) httpParams = httpParams.set('limit', params.limit.toString());
      if (params.user_id) httpParams = httpParams.set('user_id', params.user_id.toString());
      if (params.action) httpParams = httpParams.set('action', params.action);
    }
    
    return this.http.get<UserAuditLog[]>(this.apiUrl, { params: httpParams });
  }

  getAuditLogsByUser(userId: number, skip: number = 0, limit: number = 100): Observable<UserAuditLog[]> {
    return this.http.get<UserAuditLog[]>(`${this.apiUrl}/${userId}?skip=${skip}&limit=${limit}`);
  }

  getAuditLogsByActor(actorId: number, skip: number = 0, limit: number = 100): Observable<UserAuditLog[]> {
    return this.http.get<UserAuditLog[]>(`${this.apiUrl}/actor/${actorId}?skip=${skip}&limit=${limit}`);
  }
}