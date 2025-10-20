import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { NotificationService } from '../services/notification.service';

export const HttpErrorInterceptor: HttpInterceptorFn = (req, next) => {
  const notificationService = inject(NotificationService);
  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      let errorMessage = 'An unknown error occurred';
      
      if (error.error && typeof error.error === 'object') {
        // Handle FastAPI validation errors
        if (error.error.detail && Array.isArray(error.error.detail)) {
          // Extract error messages from FastAPI validation errors
          const validationErrors = error.error.detail.map((err: any) => err.msg).join('; ');
          errorMessage = validationErrors;
        } else if (error.error.detail) {
          // Handle simple detail field
          errorMessage = error.error.detail;
        } else if (error.error.message) {
          errorMessage = error.error.message;
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      notificationService.showError(errorMessage);
      return throwError(() => error);
    })
  );
};