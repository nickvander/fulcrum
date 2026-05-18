import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';

import { PaymentsService } from './payments.service';
import { environment } from '../../../environments/environment';

describe('PaymentsService', () => {
  let service: PaymentsService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [PaymentsService],
    });
    service = TestBed.inject(PaymentsService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('list() GETs /payments/ with no query params when called bare', () => {
    service.list().subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/payments/`);
    expect(req.request.method).toBe('GET');
    expect(req.request.params.keys()).toEqual([]);
    req.flush({ items: [], total: 0 });
  });

  it('list() encodes status / provider / skip / limit as query params', () => {
    service.list({ status: 'approved', provider: 'mercado_pago', skip: 20, limit: 50 }).subscribe();
    const req = httpMock.expectOne(
      (r) => r.url === `${environment.apiUrl}/payments/`,
    );
    expect(req.request.params.get('status')).toBe('approved');
    expect(req.request.params.get('provider')).toBe('mercado_pago');
    expect(req.request.params.get('skip')).toBe('20');
    expect(req.request.params.get('limit')).toBe('50');
    req.flush({ items: [], total: 0 });
  });

  it('list() omits a null status from the query string', () => {
    service.list({ status: null, skip: 0, limit: 10 }).subscribe();
    const req = httpMock.expectOne(
      (r) => r.url === `${environment.apiUrl}/payments/`,
    );
    expect(req.request.params.has('status')).toBe(false);
    expect(req.request.params.get('skip')).toBe('0');
    expect(req.request.params.get('limit')).toBe('10');
    req.flush({ items: [], total: 0 });
  });

  it('list() includes skip=0 explicitly so the backend treats it as offset 0, not unset', () => {
    // Edge case the bug-prone shape would skip: `if (skip)` would
    // drop skip=0. The implementation uses `!= null` so this stays.
    service.list({ skip: 0 }).subscribe();
    const req = httpMock.expectOne(
      (r) => r.url === `${environment.apiUrl}/payments/`,
    );
    expect(req.request.params.get('skip')).toBe('0');
    req.flush({ items: [], total: 0 });
  });

  it('get(id) GETs /payments/{id}', () => {
    service.get(42).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/payments/42`);
    expect(req.request.method).toBe('GET');
    req.flush({});
  });
});
