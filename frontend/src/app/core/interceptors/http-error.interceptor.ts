import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { TranslocoService } from '@ngneat/transloco';
import { NotificationService } from '../services/notification.service';
import { translateApiError } from '../errors/translate-api-error';

export const HttpErrorInterceptor: HttpInterceptorFn = (req, next) => {
  const notificationService = inject(NotificationService);
  const transloco = inject(TranslocoService);
  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      console.error('HTTP Error:', error);

      // Client-side errors (ErrorEvent) and connectivity failures don't
      // have a server payload to translate — handle those first.
      if (error.error instanceof ErrorEvent) {
        notificationService.showError(`Error: ${error.error.message}`);
        return throwError(() => error);
      }
      if (error.status === 0) {
        notificationService.showError(
          transloco.translate('apiErrors.network', { defaultValue: 'Unable to connect to server. Please check your internet connection.' }),
        );
        return throwError(() => error);
      }

      // FastAPI 422 validation errors return detail as an array of pydantic
      // field errors. Pre-flatten those so translateApiError sees a string
      // and falls through to its detail branch.
      const errorBody = error.error;
      if (errorBody && typeof errorBody === 'object' && Array.isArray(errorBody.detail)) {
        const joined = errorBody.detail.map((e: { msg?: string }) => e?.msg ?? '').filter(Boolean).join('; ');
        notificationService.showApiError({ error: { ...errorBody, detail: joined } });
        return throwError(() => error);
      }

      notificationService.showApiError(error);
      return throwError(() => error);
    }),
  );
};
