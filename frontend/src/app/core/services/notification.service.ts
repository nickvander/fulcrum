import { Injectable } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslocoService } from '@ngneat/transloco';
import { translateApiError } from '../errors/translate-api-error';

@Injectable({
  providedIn: 'root',
})
export class NotificationService {
  constructor(
    private readonly snackBar: MatSnackBar,
    private readonly transloco: TranslocoService
  ) { }

  showSuccess(message: string): void {
    this.snackBar.open(message, this.transloco.translate('common.close'), {
      duration: 3000,
      panelClass: ['snackbar-success'],
    });
  }

  showError(message: string): void {
    this.snackBar.open(message, this.transloco.translate('common.close'), {
      duration: 5000,
      panelClass: ['snackbar-error'],
    });
  }

  /**
   * Resolve a backend HTTP error to its localized message and show it.
   * Uses translateApiError, so a `{code, params}` payload is translated
   * via transloco; otherwise falls back to `err.error.detail`, then
   * `err.message`, then the supplied `fallbackKey` (default `apiErrors.unknown`).
   */
  showApiError(err: unknown, fallbackKey?: string): void {
    this.showError(translateApiError(err, this.transloco, fallbackKey));
  }
}
