import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';

import { InventoryCountService } from './inventory-count.service';
import { environment } from '../../../environments/environment';

describe('InventoryCountService', () => {
  let service: InventoryCountService;
  let httpMock: HttpTestingController;
  const apiUrl = `${environment.apiUrl}/inventory-counts`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [InventoryCountService],
    });
    service = TestBed.inject(InventoryCountService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('list() GETs /inventory-counts/ without params by default', () => {
    service.list().subscribe();
    const req = httpMock.expectOne(`${apiUrl}/`);
    expect(req.request.method).toBe('GET');
    // No query string set when filter is omitted.
    expect(req.request.params.keys().length).toBe(0);
    req.flush([]);
  });

  it('list() forwards the status filter as a query param', () => {
    service.list({ status: 'in_progress' }).subscribe();
    const req = httpMock.expectOne(r =>
      r.url === `${apiUrl}/` && r.params.get('status') === 'in_progress',
    );
    expect(req.request.method).toBe('GET');
    req.flush([]);
  });

  it('start() POSTs the location + notes to /', () => {
    service.start({ location: 'aisle-3', notes: 'spot check' }).subscribe();
    const req = httpMock.expectOne(`${apiUrl}/`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ location: 'aisle-3', notes: 'spot check' });
    req.flush({});
  });

  it('get() GETs /{id}', () => {
    service.get(42).subscribe();
    const req = httpMock.expectOne(`${apiUrl}/42`);
    expect(req.request.method).toBe('GET');
    req.flush({});
  });

  it('addItem() POSTs the SKU body to /{id}/items', () => {
    service.addItem(7, 'ABC-123').subscribe();
    const req = httpMock.expectOne(`${apiUrl}/7/items`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ sku: 'ABC-123' });
    req.flush({});
  });

  it('updateCount() PATCHes the counted_quantity to /{id}/items/{itemId}', () => {
    service.updateCount(7, 99, 12).subscribe();
    const req = httpMock.expectOne(`${apiUrl}/7/items/99`);
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ counted_quantity: 12 });
    req.flush({});
  });

  it('updateCount() forwards null to clear the counted value', () => {
    service.updateCount(7, 99, null).subscribe();
    const req = httpMock.expectOne(`${apiUrl}/7/items/99`);
    expect(req.request.body).toEqual({ counted_quantity: null });
    req.flush({});
  });

  it('removeItem() DELETEs /{id}/items/{itemId}', () => {
    service.removeItem(7, 99).subscribe();
    const req = httpMock.expectOne(`${apiUrl}/7/items/99`);
    expect(req.request.method).toBe('DELETE');
    req.flush(null);
  });

  it('commit() POSTs an empty body to /{id}/commit', () => {
    service.commit(7).subscribe();
    const req = httpMock.expectOne(`${apiUrl}/7/commit`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({});
    req.flush({});
  });

  it('cancel() POSTs an empty body to /{id}/cancel', () => {
    service.cancel(7).subscribe();
    const req = httpMock.expectOne(`${apiUrl}/7/cancel`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({});
    req.flush({});
  });
});
