import { Component, OnDestroy } from '@angular/core';
import { MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { Subject, takeUntil } from 'rxjs';
import { BulkImportService } from '../../services/bulk-import.service';

@Component({
  selector: 'app-user-bulk-import-dialog',
  templateUrl: './user-bulk-import-dialog.html',
  styleUrls: ['./user-bulk-import-dialog.scss'],
  standalone: true,
  imports: [
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    MatTableModule,
    MatSnackBarModule,
    MatTooltipModule,
    TranslocoModule
  ],
  providers: [BulkImportService]
})
export class UserBulkImportDialogComponent implements OnDestroy {
  selectedFile: File | null = null;
  isUploading = false;
  importResult: any = null;
  private destroy$ = new Subject<void>();

  constructor(
    public dialogRef: MatDialogRef<UserBulkImportDialogComponent>,
    private bulkImportService: BulkImportService,
    private snackBar: MatSnackBar,
    private translocoService: TranslocoService
  ) { }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  onFileSelected(event: any): void {
    const file: File = event.target.files[0];
    if (file) {
      const validation = this.bulkImportService.validateFile(file);
      if (!validation.valid) {
        this.snackBar.open(validation.error!, this.translocoService.translate('common.close'), { duration: 3000 });
        return;
      }
      this.selectedFile = file;
      this.importResult = null;
    }
  }

  downloadTemplate(): void {
    const csvContent = this.bulkImportService.getTemplateContent();
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'users_import_template.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  }

  upload(): void {
    if (!this.selectedFile) return;

    this.isUploading = true;
    this.bulkImportService.processFile(this.selectedFile)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (result) => {
          this.isUploading = false;
          this.importResult = result;
          if (result.failed_users.length === 0) {
            this.snackBar.open(this.translocoService.translate('users.messages.importSuccess'), this.translocoService.translate('common.close'), { duration: 3000 });
          } else {
            this.snackBar.open(this.translocoService.translate('users.messages.importWithErrors'), this.translocoService.translate('common.close'), { duration: 5000 });
          }
        },
        error: (error) => {
          this.isUploading = false;
          console.error('Import failed', error);
          this.snackBar.open(error.error?.detail || this.translocoService.translate('users.errors.importFailed'), this.translocoService.translate('common.close'), { duration: 5000 });
        }
      });
  }

  close(): void {
    this.dialogRef.close(this.importResult ? true : false);
  }

  copyPassword(password: string): void {
    navigator.clipboard.writeText(password).then(() => {
      this.snackBar.open(this.translocoService.translate('common.messages.copied'), this.translocoService.translate('common.close'), { duration: 2000 });
    });
  }

  copyAll(): void {
    if (!this.importResult || !this.importResult.created_users) return;

    const csvContent = this.bulkImportService.formatResultsAsCsv(this.importResult.created_users);

    navigator.clipboard.writeText(csvContent).then(() => {
      this.snackBar.open(this.translocoService.translate('common.messages.copied'), this.translocoService.translate('common.close'), { duration: 2000 });
    });
  }
}
