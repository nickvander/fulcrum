import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { Subject, takeUntil } from 'rxjs';

import { translateApiError } from '../../../core/errors/translate-api-error';
import {
  CatalogImportService,
  ImportTemplate,
  ImportTemplatePreview,
} from '../../services/catalog-import.service';

type Step = 'list' | 'create';

/**
 * The list of Fulcrum canonical fields a CSV header can be mapped to.
 * Mirrors `_ALLOWED_CANONICAL_FIELDS` in `endpoints/catalog_imports.py`;
 * keep these two lists in sync. The Skip / unmapped option (empty
 * string) is the default so a header doesn't have to be mapped if the
 * supplier sends extra junk columns.
 */
const CANONICAL_FIELDS = [
  { key: '',                     label: 'catalogImportTemplates.unmapped' },
  { key: 'sku',                  label: 'catalogImportTemplates.fieldSku' },
  { key: 'name',                 label: 'catalogImportTemplates.fieldName' },
  { key: 'description',          label: 'catalogImportTemplates.fieldDescription' },
  { key: 'cost_price',           label: 'catalogImportTemplates.fieldCostPrice' },
  { key: 'default_resale_price', label: 'catalogImportTemplates.fieldResalePrice' },
  { key: 'category',             label: 'catalogImportTemplates.fieldCategory' },
  { key: 'brand',                label: 'catalogImportTemplates.fieldBrand' },
  { key: 'supplier_sku',         label: 'catalogImportTemplates.fieldSupplierSku' },
];

@Component({
  selector: 'app-catalog-import-templates',
  templateUrl: './catalog-import-templates.html',
  styleUrls: ['./catalog-import-templates.scss'],
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatListModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSnackBarModule,
    MatTooltipModule,
    TranslocoModule,
  ],
})
export class CatalogImportTemplatesDialogComponent implements OnInit, OnDestroy {
  step: Step = 'list';
  templates: ImportTemplate[] = [];
  loading = false;
  saving = false;

  // Create form
  templateName = '';
  preview: ImportTemplatePreview | null = null;
  /** {sourceHeader: canonicalField} mapping the user is editing. */
  headerMap: { [sourceHeader: string]: string } = {};
  /** Whichever the user changed last (used to disable Save when name empty). */
  readonly canonicalFields = CANONICAL_FIELDS;

  private destroy$ = new Subject<void>();

  constructor(
    public dialogRef: MatDialogRef<CatalogImportTemplatesDialogComponent>,
    private service: CatalogImportService,
    private snackBar: MatSnackBar,
    private transloco: TranslocoService,
  ) {}

  ngOnInit(): void {
    this.loadTemplates();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private loadTemplates(): void {
    this.loading = true;
    this.service.listTemplates()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (list) => {
          this.templates = list || [];
          this.loading = false;
        },
        error: () => (this.loading = false),
      });
  }

  startCreate(): void {
    this.step = 'create';
    this.templateName = '';
    this.preview = null;
    this.headerMap = {};
  }

  /** Fired by the file input on the Create step. Asks the backend to
   *  parse the file's headers + first 5 rows so the user can map them. */
  onSampleSelected(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    this.loading = true;
    this.service.previewForMapping(file)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (preview) => {
          this.preview = preview;
          // Pre-fill the dropdowns from the auto-detector's best guess so
          // the user only has to fix what was missed.
          this.headerMap = {};
          for (const [canonical, header] of Object.entries(preview.detected_field_map || {})) {
            this.headerMap[header] = canonical;
          }
          // Ensure every header has at least an empty (unmapped) entry so
          // ngModel doesn't choke on undefined.
          for (const h of preview.headers) {
            if (!(h in this.headerMap)) {
              this.headerMap[h] = '';
            }
          }
          this.loading = false;
        },
        error: (err) => {
          this.loading = false;
          this.snack(translateApiError(err, this.transloco, 'catalogImportTemplates.errors.previewFailed'));
        },
      });
  }

  canSave(): boolean {
    if (this.saving || !this.preview) return false;
    if (!this.templateName.trim()) return false;
    // At minimum one header must be mapped to `name` — that's the parser's
    // hard requirement, so guarding it here saves a round-trip.
    return Object.values(this.headerMap).includes('name');
  }

  saveTemplate(): void {
    if (!this.canSave()) return;
    this.saving = true;
    const cleaned: { [k: string]: string } = {};
    for (const [header, canonical] of Object.entries(this.headerMap)) {
      if (canonical) cleaned[header] = canonical;
    }
    this.service.createTemplate({
      name: this.templateName.trim(),
      column_map: cleaned,
    })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.saving = false;
          this.snack(this.transloco.translate('catalogImportTemplates.saved'));
          this.step = 'list';
          this.loadTemplates();
        },
        error: (err) => {
          this.saving = false;
          this.snack(translateApiError(err, this.transloco, 'catalogImportTemplates.errors.saveFailed'));
        },
      });
  }

  deleteTemplate(template: ImportTemplate): void {
    const confirmed = window.confirm(
      this.transloco.translate('catalogImportTemplates.confirmDelete', { name: template.name }),
    );
    if (!confirmed) return;
    this.service.deleteTemplate(template.id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.templates = this.templates.filter(t => t.id !== template.id);
        },
        error: (err) => {
          this.snack(translateApiError(err, this.transloco, 'catalogImportTemplates.errors.deleteFailed'));
        },
      });
  }

  cancelCreate(): void {
    this.step = 'list';
  }

  close(): void {
    // Pass the latest template list back so the caller can refresh its
    // dropdown without an extra round-trip.
    this.dialogRef.close(this.templates);
  }

  private snack(message: string): void {
    this.snackBar.open(message, this.transloco.translate('common.close'), { duration: 4000 });
  }
}
