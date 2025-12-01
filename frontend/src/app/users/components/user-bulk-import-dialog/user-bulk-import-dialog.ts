import { Component, OnDestroy } from '@angular/core';
import { MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { UserService } from '../../services/user.service';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, takeUntil } from 'rxjs';

@Component({
  selector: 'app-user-bulk-import-dialog',
  templateUrl: './user-bulk-import-dialog.html',
  styleUrls: ['./user-bulk-import-dialog.scss'],
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    MatTableModule,
    MatSnackBarModule,
    MatTooltipModule
  ]
})
export class UserBulkImportDialogComponent implements OnDestroy {
  selectedFile: File | null = null;
  isUploading = false;
  importResult: any = null;
  private destroy$ = new Subject<void>();

  constructor(
    public dialogRef: MatDialogRef<UserBulkImportDialogComponent>,
    private userService: UserService,
    private snackBar: MatSnackBar
  ) { }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  onFileSelected(event: any): void {
    const file: File = event.target.files[0];
    if (file) {
      if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
        this.snackBar.open('Please select a CSV file', 'Close', { duration: 3000 });
        return;
      }
      this.selectedFile = file;
      this.importResult = null;
    }
  }

  downloadTemplate(): void {
    const csvContent = 'email,first_name,last_name,user_type\nuser@example.com,John,Doe,employee';
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
    this.userService.bulkImportUsers(this.selectedFile)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (result) => {
          this.isUploading = false;
          this.importResult = result;
          if (result.failed_users.length === 0) {
            this.snackBar.open('Import completed successfully', 'Close', { duration: 3000 });
          } else {
            this.snackBar.open('Import completed with some errors', 'Close', { duration: 5000 });
          }
        },
        error: (error) => {
          this.isUploading = false;
          console.error('Import failed', error);
          this.snackBar.open(error.error?.detail || 'Import failed', 'Close', { duration: 5000 });
        }
      });
  }

  close(): void {
    this.dialogRef.close(this.importResult ? true : false);
  }

  copyPassword(password: string): void {
    navigator.clipboard.writeText(password).then(() => {
      this.snackBar.open('Password copied to clipboard', 'Close', { duration: 2000 });
    });
  }

  copyAll(): void {
    if (!this.importResult || !this.importResult.created_users) return;

    const headers = ['Email', 'Temporary Password'];
    const rows = this.importResult.created_users.map((u: any) => `${u.email},${u.temporary_password}`);
    const csvContent = [headers.join(','), ...rows].join('\n');

    navigator.clipboard.writeText(csvContent).then(() => {
      this.snackBar.open('All results copied to clipboard', 'Close', { duration: 2000 });
    });
  }
}
