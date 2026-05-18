import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

/**
 * CSV/PDF download endpoints for the velocity / margin / stockout
 * reports. These reports do not have a JSON shape on the frontend yet —
 * the dashboard widget only triggers blob downloads, and the backend
 * report_export helper handles content-type + filename headers.
 *
 * Default `limit` is 2000 to match the backend (the "give me
 * everything" use case for spreadsheet triage). Window/imminent/watch
 * defaults are mirrored from the backend Query defaults so a caller
 * that just wants "now" can pass no arguments.
 */
@Injectable({ providedIn: 'root' })
export class AnalyticsReportsService {
  private apiUrl = `${environment.apiUrl}/reports`;

  constructor(private http: HttpClient) {}

  exportVelocityCsv(windowDays = 30, limit = 2000): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/velocity/export`, { window_days: windowDays, limit });
  }

  exportVelocityPdf(windowDays = 30, limit = 2000): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/velocity/export-pdf`, { window_days: windowDays, limit });
  }

  exportMarginCsv(windowDays = 30, limit = 2000): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/margin/export`, { window_days: windowDays, limit });
  }

  exportMarginPdf(windowDays = 30, limit = 2000): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/margin/export-pdf`, { window_days: windowDays, limit });
  }

  exportStockoutCsv(
    windowDays = 30,
    imminentDays = 7,
    watchDays = 14,
    limit = 2000,
  ): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/stockout/export`, {
      window_days: windowDays,
      imminent_days: imminentDays,
      watch_days: watchDays,
      limit,
    });
  }

  exportStockoutPdf(
    windowDays = 30,
    imminentDays = 7,
    watchDays = 14,
    limit = 2000,
  ): Observable<Blob> {
    return this.blobGet(`${this.apiUrl}/stockout/export-pdf`, {
      window_days: windowDays,
      imminent_days: imminentDays,
      watch_days: watchDays,
      limit,
    });
  }

  private blobGet(url: string, params: Record<string, number>): Observable<Blob> {
    let httpParams = new HttpParams();
    for (const [k, v] of Object.entries(params)) {
      httpParams = httpParams.set(k, String(v));
    }
    return this.http.get(url, { params: httpParams, responseType: 'blob' });
  }
}
