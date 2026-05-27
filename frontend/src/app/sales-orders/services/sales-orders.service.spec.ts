import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';

import { SalesOrdersService } from './sales-orders.service';
import { environment } from '../../../environments/environment';

describe('SalesOrdersService — returns workflow', () => {
  let service: SalesOrdersService;
  let httpMock: HttpTestingController;
  const baseUrl = `${environment.apiUrl}/sales-orders`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [SalesOrdersService],
    });
    service = TestBed.inject(SalesOrdersService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('listReturns(id) GETs /sales-orders/{id}/returns', () => {
    service.listReturns(42).subscribe();
    const req = httpMock.expectOne(`${baseUrl}/42/returns`);
    expect(req.request.method).toBe('GET');
    req.flush([]);
  });

  it('recordReturn(id, payload) POSTs the payload as-is', () => {
    const payload = {
      lines: [{ order_item_id: 10, quantity: 2 }],
      reason: 'buyer remorse',
      notes: null,
    };
    service.recordReturn(7, payload).subscribe();
    const req = httpMock.expectOne(`${baseUrl}/7/returns`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(payload);
    req.flush([{ id: 1, order_id: 7, quantity: 2, received_at: '2026-05-19T00:00:00Z' }]);
  });
});
