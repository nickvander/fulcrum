import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

/**
 * Triggers blob downloads for report exports. Centralizes the "create
 * temporary <a> with object URL, click it, revoke" dance so each widget
 * that has Export CSV / Export PDF buttons doesn't repeat the same eight
 * lines. Pairs with the backend's `report_export` module — every report
 * uses the same date-stamped filename convention (`stem-YYYY-MM-DD.ext`),
 * which this service rebuilds client-side so the file lands in
 * Downloads/ with the expected name even when the user is offline.
 */
@Injectable({ providedIn: 'root' })
export class ReportDownloadService {
  /**
   * Subscribe to `req`, write the resulting Blob to a temporary anchor,
   * and click it. The download fails silently if the request errors —
   * `HttpErrorInterceptor` already surfaces backend messages.
   *
   * @param req       Observable that emits the file body (responseType
   *                  must already be 'blob' at the caller).
   * @param stem      Filename stem matching the backend's
   *                  `ReportTable.filename_stem`. Today's date and the
   *                  extension are appended automatically.
   * @param ext       'csv' or 'pdf'.
   */
  download(req: Observable<Blob>, stem: string, ext: 'csv' | 'pdf'): void {
    req.subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        const today = new Date().toISOString().slice(0, 10);
        link.download = `${stem}-${today}.${ext}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      },
      error: () => {
        // HttpErrorInterceptor renders the backend's localized message.
      },
    });
  }
}
