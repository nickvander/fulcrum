import { ComponentFixture, TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { PurchaseOrderListComponent } from './purchase-order-list.component';
import { SuppliersService, SupplierDocumentImportReview } from '../../suppliers.service';
import { DateRangeService } from '../../../shared/services/date-range.service';
import { of } from 'rxjs';
import { RouterTestingModule } from '@angular/router/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { MatTableModule } from '@angular/material/table';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSortModule } from '@angular/material/sort';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { CommonModule } from '@angular/common';
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { MatPaginatorModule } from '@angular/material/paginator';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { TranslocoTestingModule } from '@ngneat/transloco';

describe('PurchaseOrderListComponent', () => {
  let component: PurchaseOrderListComponent;
  let fixture: ComponentFixture<PurchaseOrderListComponent>;

  const staleReview = (): SupplierDocumentImportReview => ({
    id: 1,
    file_name: 'old-import.pdf',
    content_type: 'application/pdf',
    source: 'supplier_document',
    status: 'pending',
    mode: 'create',
    supplier_id: null,
    purchase_order_id: null,
    extracted_data: {} as any,
    warnings: [],
    created_at: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
    reviewed_at: null
  });

  const freshReview = (): SupplierDocumentImportReview => ({
    id: 2,
    file_name: 'fresh-import.pdf',
    content_type: 'application/pdf',
    source: 'supplier_document',
    status: 'pending',
    mode: 'create',
    supplier_id: null,
    purchase_order_id: null,
    extracted_data: {} as any,
    warnings: [],
    created_at: new Date().toISOString(),
    reviewed_at: null
  });

  const suppliersServiceMock = {
    getSuppliers: () => of([]),
    getPurchaseOrders: () => of([]),
    getImportReviews: vi.fn((status: string | null = 'pending') => {
      if (status === 'approved,rejected' || status === 'all') {
        return of([]);
      }
      return of([staleReview(), freshReview()]);
    }),
    bulkRejectImportReviews: vi.fn(() =>
      of({ rejected_count: 1, rejected_ids: [1], skipped_ids: [] })
    )
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [],
      imports: [
        PurchaseOrderListComponent,
        CommonModule,
        MatTableModule,
        MatPaginatorModule,
        MatSortModule,
        MatIconModule,
        MatButtonModule,
        MatSelectModule,
        MatCardModule,
        MatFormFieldModule,
        MatInputModule,
        BrowserAnimationsModule,
        RouterTestingModule,
        HttpClientTestingModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, es: {} },
          translocoConfig: { availableLangs: ['en', 'es'], defaultLang: 'en' }
        })
      ],
      providers: [
        { provide: SuppliersService, useValue: suppliersServiceMock },
        DateRangeService
      ],
      schemas: [CUSTOM_ELEMENTS_SCHEMA]
    })
      .compileComponents();

    fixture = TestBed.createComponent(PurchaseOrderListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('counts stale pending reviews and surfaces the bulk-reject affordance', () => {
    expect(component.staleReviewCount).toBe(1);
  });

  it('bulk reject calls the service with a stale_before cutoff and reloads data', () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const bulkRejectSpy = suppliersServiceMock.bulkRejectImportReviews as ReturnType<typeof vi.fn>;
    bulkRejectSpy.mockClear();
    component.bulkRejectStale();
    expect(bulkRejectSpy).toHaveBeenCalled();
    const calls = bulkRejectSpy.mock.calls;
    const payload = (calls.length ? calls[calls.length - 1][0] : {}) as { stale_before?: string; review_ids?: number[] };
    expect(payload.stale_before).toBeTruthy();
    expect(payload.review_ids).toBeUndefined();
  });

  it('switching to history filter requests the approved+rejected status set', () => {
    const getReviewsSpy = suppliersServiceMock.getImportReviews as ReturnType<typeof vi.fn>;
    getReviewsSpy.mockClear();
    component.setReviewFilter('history');
    expect(getReviewsSpy).toHaveBeenCalledWith('approved,rejected');
  });
});
