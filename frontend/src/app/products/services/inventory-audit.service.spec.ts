import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';

import { InventoryAuditService } from './inventory-audit.service';
import { environment } from '../../../environments/environment';

describe('InventoryAuditService', () => {
  let service: InventoryAuditService;
  let httpMock: HttpTestingController;
  const baseUrl = `${environment.apiUrl}/reports/inventory-adjustments`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [InventoryAuditService],
    });
    service = TestBed.inject(InventoryAuditService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('list() GETs the audit endpoint with no query params by default', () => {
    service.list().subscribe();
    const req = httpMock.expectOne(r => r.url === baseUrl);
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('product_id')).toBeNull();
    expect(req.request.params.get('reason_code')).toBeNull();
    req.flush({ rows: [], total: 0 });
  });

  it('list() forwards the reasonCode filter as `reason_code` (snake_case)', () => {
    service.list({ reasonCode: 'shrinkage' }).subscribe();
    const req = httpMock.expectOne(r => r.url === baseUrl);
    expect(req.request.params.get('reason_code')).toBe('shrinkage');
    req.flush({ rows: [], total: 0 });
  });

  it("list() forwards the magic 'none' filter for legacy uncategorized rows", () => {
    service.list({ reasonCode: 'none' }).subscribe();
    const req = httpMock.expectOne(r => r.url === baseUrl);
    expect(req.request.params.get('reason_code')).toBe('none');
    req.flush({ rows: [], total: 0 });
  });

  it('list() forwards productId + after/before + skip/limit alongside the reason filter', () => {
    service
      .list({
        productId: 12,
        after: '2026-01-01T00:00:00',
        before: '2026-01-31T23:59:59',
        reasonCode: 'theft',
        skip: 50,
        limit: 25,
      })
      .subscribe();
    const req = httpMock.expectOne(r => r.url === baseUrl);
    expect(req.request.params.get('product_id')).toBe('12');
    expect(req.request.params.get('after')).toBe('2026-01-01T00:00:00');
    expect(req.request.params.get('before')).toBe('2026-01-31T23:59:59');
    expect(req.request.params.get('reason_code')).toBe('theft');
    expect(req.request.params.get('skip')).toBe('50');
    expect(req.request.params.get('limit')).toBe('25');
    req.flush({ rows: [], total: 0 });
  });

  it('listReasonCodes() GETs the canonical enum list endpoint', () => {
    service.listReasonCodes().subscribe(codes => {
      expect(codes).toEqual(['shrinkage', 'recount', 'damage']);
    });
    const req = httpMock.expectOne(r => r.url === `${baseUrl}/reason-codes`);
    expect(req.request.method).toBe('GET');
    req.flush(['shrinkage', 'recount', 'damage']);
  });

  it('exportCsv() forwards filters as a blob request', () => {
    service.exportCsv({ reasonCode: 'damage', productId: 7 }).subscribe();
    const req = httpMock.expectOne(r => r.url === `${baseUrl}/export`);
    expect(req.request.method).toBe('GET');
    expect(req.request.responseType).toBe('blob');
    expect(req.request.params.get('reason_code')).toBe('damage');
    expect(req.request.params.get('product_id')).toBe('7');
    req.flush(new Blob());
  });

  it('exportPdf() forwards filters identically', () => {
    service.exportPdf({ reasonCode: 'recount' }).subscribe();
    const req = httpMock.expectOne(r => r.url === `${baseUrl}/export-pdf`);
    expect(req.request.params.get('reason_code')).toBe('recount');
    req.flush(new Blob());
  });

  it('reverse() POSTs to the per-row reverse endpoint with a null note by default', () => {
    service.reverse(42).subscribe();
    const req = httpMock.expectOne(r => r.url === `${baseUrl}/42/reverse`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ note: null });
    req.flush({ id: 99, adjustment: 5, reverses_adjustment_id: 42 });
  });

  it('reverse() forwards a note when provided', () => {
    service.reverse(7, 'miscount').subscribe();
    const req = httpMock.expectOne(r => r.url === `${baseUrl}/7/reverse`);
    expect(req.request.body).toEqual({ note: 'miscount' });
    req.flush({ id: 100, adjustment: -2, reverses_adjustment_id: 7 });
  });
});
