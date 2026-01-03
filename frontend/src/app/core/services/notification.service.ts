import { Injectable } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslocoService } from '@ngneat/transloco';

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
}
