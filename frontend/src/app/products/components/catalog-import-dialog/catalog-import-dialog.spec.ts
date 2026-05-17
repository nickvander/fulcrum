import type { MockedObject } from 'vitest';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { SuppliersService } from '../../../suppliers/suppliers.service';
import {
  CatalogImportApproveResponse,
  CatalogImportReview,
  CatalogImportService,
} from '../../services/catalog-import.service';
import { CatalogImportDialogComponent } from './catalog-import-dialog';

function makeReview(overrides: Partial<CatalogImportReview> = {}): CatalogImportReview {
  return {
    id: 7,
    file_name: 'catalog.csv',
    content_type: 'text/csv',
    source: 'csv',
    status: 'pending',
    supplier_id: null,
    extracted_data: {
      items: [
        {
          sku: 'A-1',
          name: 'Widget',
          description: null,
          cost_price: 5,
          default_resale_price: 10,
          category: null,
          brand: null,
          supplier_sku: null,
          raw: {},
          warnings: [],
          selected: true,
        },
        {
          sku: 'A-2',
          name: 'Gadget',
          description: null,
          cost_price: 7,
          default_resale_price: 15,
          category: null,
          brand: null,
          supplier_sku: null,
          raw: {},
          warnings: [],
          selected: true,
        },
      ],
    },
    warnings: [],
    created_at: '2026-05-17T00:00:00Z',
    reviewed_at: null,
    ...overrides,
  };
}

describe('CatalogImportDialogComponent', () => {
  let component: CatalogImportDialogComponent;
  let fixture: ComponentFixture<CatalogImportDialogComponent>;
  let serviceSpy: MockedObject<CatalogImportService>;
  let suppliersSpy: MockedObject<SuppliersService>;
  let dialogRefSpy: MockedObject<MatDialogRef<CatalogImportDialogComponent>>;

  beforeEach(async () => {
    serviceSpy = {
      upload: vi.fn(),
      approve: vi.fn(),
      reject: vi.fn(),
      capabilities: vi.fn().mockReturnValue(
        of({
          csv: true,
          ai: false,
          ai_enabled: false,
          ai_configured: false,
          ai_provider: 'google',
          accepted_extensions: ['csv', 'tsv', 'txt'],
        }),
      ),
    } as unknown as MockedObject<CatalogImportService>;

    suppliersSpy = {
      getSuppliers: vi.fn().mockReturnValue(of([])),
    } as unknown as MockedObject<SuppliersService>;

    dialogRefSpy = {
      close: vi.fn(),
    } as unknown as MockedObject<MatDialogRef<CatalogImportDialogComponent>>;

    await TestBed.configureTestingModule({
      imports: [
        CatalogImportDialogComponent,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({ langs: { en: {}, 'es-MX': {} } }),
      ],
      schemas: [NO_ERRORS_SCHEMA],
      providers: [
        provideRouter([]),
        { provide: MatDialogRef, useValue: dialogRefSpy },
        { provide: CatalogImportService, useValue: serviceSpy },
        { provide: SuppliersService, useValue: suppliersSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CatalogImportDialogComponent);
    component = fixture.componentInstance;
    vi.spyOn((component as any).snackBar as MatSnackBar, 'open');
  });

  afterEach(() => {
    fixture.destroy();
    vi.restoreAllMocks();
  });

  it('creates and loads suppliers on init', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
    expect(suppliersSpy.getSuppliers).toHaveBeenCalledWith(0, 500);
  });

  it('rejects a PDF when AI is not configured', () => {
    fixture.detectChanges();  // triggers capabilities() default mock
    const file = new File([''], 'thing.pdf', { type: 'application/pdf' });
    component.onFileSelected({ target: { files: [file] } } as any);
    expect(component.selectedFile).toBeNull();
    expect((component as any).snackBar.open).toHaveBeenCalled();
  });

  it('accepts a CSV file by name even when type is empty', () => {
    fixture.detectChanges();
    const file = new File([''], 'catalog.csv', { type: '' });
    component.onFileSelected({ target: { files: [file] } } as any);
    expect(component.selectedFile).toBe(file);
  });

  it('accepts a PDF when capabilities report AI is ready', () => {
    serviceSpy.capabilities.mockReturnValue(
      of({
        csv: true,
        ai: true,
        ai_enabled: true,
        ai_configured: true,
        ai_provider: 'google',
        accepted_extensions: ['csv', 'tsv', 'txt', 'pdf', 'png', 'jpg', 'jpeg'],
      }),
    );
    fixture.detectChanges();
    const pdf = new File([''], 'catalog.pdf', { type: 'application/pdf' });
    component.onFileSelected({ target: { files: [pdf] } } as any);
    expect(component.selectedFile).toBe(pdf);
    expect(component.acceptAttr()).toContain('.pdf');
  });

  it('exposes acceptAttr() with only CSV extensions when AI is off', () => {
    fixture.detectChanges();
    expect(component.acceptAttr()).toBe('.csv,.tsv,.txt');
  });

  it('upload() transitions to review step with returned items', () => {
    component.selectedFile = new File(['x'], 'c.csv', { type: 'text/csv' });
    serviceSpy.upload.mockReturnValue(of(makeReview()));

    component.upload();

    expect(serviceSpy.upload).toHaveBeenCalledWith(component.selectedFile, null);
    expect(component.step).toBe('review');
    expect(component.review!.extracted_data.items.length).toBe(2);
    expect(component.selectedCount()).toBe(2);
  });

  it('toggleAll(false) deselects every item, blocking approve()', () => {
    component.review = makeReview();
    component.step = 'review';
    component.toggleAll(false);
    expect(component.selectedCount()).toBe(0);

    component.approve();
    expect(serviceSpy.approve).not.toHaveBeenCalled();
    expect((component as any).snackBar.open).toHaveBeenCalled();
  });

  it('approve() posts selected items + supplier and shows done step on success', () => {
    component.review = makeReview();
    component.step = 'review';
    component.selectedSupplierId = 42;
    const resp: CatalogImportApproveResponse = {
      import_review: { ...component.review, status: 'approved' },
      created_product_ids: [100, 101],
      skipped_count: 0,
      skipped_reasons: [],
    };
    serviceSpy.approve.mockReturnValue(of(resp));

    component.approve();

    expect(serviceSpy.approve).toHaveBeenCalledWith(7, component.review.extracted_data.items, 42);
    expect(component.step).toBe('done');
    expect(component.approval).toBe(resp);
  });

  it('reject() calls service and closes the dialog with false', () => {
    component.review = makeReview();
    serviceSpy.reject.mockReturnValue(of(component.review));
    component.reject();
    expect(serviceSpy.reject).toHaveBeenCalledWith(7);
    expect(dialogRefSpy.close).toHaveBeenCalledWith(false);
  });

  it('shows snackbar on upload error', () => {
    component.selectedFile = new File(['x'], 'c.csv', { type: 'text/csv' });
    serviceSpy.upload.mockReturnValue(throwError(() => ({ status: 400, error: {} })));
    component.upload();
    expect(component.step).toBe('upload');
    expect((component as any).snackBar.open).toHaveBeenCalled();
  });
});
