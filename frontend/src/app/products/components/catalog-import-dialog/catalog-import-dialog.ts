import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { Subject, takeUntil } from 'rxjs';

import { translateApiError } from '../../../core/errors/translate-api-error';
import { Supplier } from '../../../shared/models/supplier.model';
import { SuppliersService } from '../../../suppliers/suppliers.service';
import {
  CatalogImportApproveResponse,
  CatalogImportItem,
  CatalogImportReview,
  CatalogImportService,
} from '../../services/catalog-import.service';

type Step = 'upload' | 'review' | 'done';

@Component({
  selector: 'app-catalog-import-dialog',
  templateUrl: './catalog-import-dialog.html',
  styleUrls: ['./catalog-import-dialog.scss'],
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatCheckboxModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSnackBarModule,
    MatTableModule,
    TranslocoModule,
  ],
})
export class CatalogImportDialogComponent implements OnInit, OnDestroy {
  step: Step = 'upload';
  selectedFile: File | null = null;
  selectedSupplierId: number | null = null;
  isBusy = false;
  review: CatalogImportReview | null = null;
  approval: CatalogImportApproveResponse | null = null;
  suppliers: Supplier[] = [];
  readonly displayedColumns = ['selected', 'sku', 'name', 'price', 'cost', 'brand', 'rowWarnings'];

  private destroy$ = new Subject<void>();

  constructor(
    public dialogRef: MatDialogRef<CatalogImportDialogComponent, boolean>,
    private service: CatalogImportService,
    private suppliersService: SuppliersService,
    private snackBar: MatSnackBar,
    private transloco: TranslocoService,
  ) {}

  ngOnInit(): void {
    this.suppliersService
      .getSuppliers(0, 500)
      .pipe(takeUntil(this.destroy$))
      .subscribe({ next: (suppliers) => (this.suppliers = suppliers || []) });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  onFileSelected(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    const isCsv =
      file.type === 'text/csv' ||
      file.type === 'text/plain' ||
      file.name.toLowerCase().endsWith('.csv') ||
      file.name.toLowerCase().endsWith('.tsv');
    if (!isCsv) {
      this.snack(this.transloco.translate('products.catalogImport.errors.csvOnly'));
      return;
    }
    this.selectedFile = file;
  }

  downloadTemplate(): void {
    const csv = this.transloco.translate('products.catalogImport.templateContent');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'catalog_import_template.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  }

  upload(): void {
    if (!this.selectedFile) return;
    this.isBusy = true;
    this.service
      .upload(this.selectedFile, this.selectedSupplierId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (review) => {
          this.isBusy = false;
          this.review = review;
          this.step = 'review';
        },
        error: (err) => {
          this.isBusy = false;
          this.snack(translateApiError(err, this.transloco, 'products.catalogImport.errors.uploadFailed'));
        },
      });
  }

  selectedCount(): number {
    return (this.review?.extracted_data.items || []).filter((i) => i.selected).length;
  }

  toggleAll(checked: boolean): void {
    if (!this.review) return;
    this.review.extracted_data.items.forEach((item) => {
      if (item.name) {
        item.selected = checked;
      }
    });
  }

  trackByIndex(index: number): number {
    return index;
  }

  approve(): void {
    if (!this.review) return;
    const items = this.review.extracted_data.items;
    if (!items.some((i) => i.selected)) {
      this.snack(this.transloco.translate('apiErrors.catalogImport.nothingSelected'));
      return;
    }
    this.isBusy = true;
    this.service
      .approve(this.review.id, items, this.selectedSupplierId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (resp) => {
          this.isBusy = false;
          this.approval = resp;
          this.review = resp.import_review;
          this.step = 'done';
        },
        error: (err) => {
          this.isBusy = false;
          this.snack(translateApiError(err, this.transloco, 'products.catalogImport.errors.approveFailed'));
        },
      });
  }

  reject(): void {
    if (!this.review) return;
    this.isBusy = true;
    this.service
      .reject(this.review.id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.isBusy = false;
          this.dialogRef.close(false);
        },
        error: (err) => {
          this.isBusy = false;
          this.snack(translateApiError(err, this.transloco, 'products.catalogImport.errors.rejectFailed'));
        },
      });
  }

  close(): void {
    this.dialogRef.close(this.approval ? true : false);
  }

  private snack(message: string): void {
    this.snackBar.open(message, this.transloco.translate('common.close'), { duration: 4000 });
  }
}
