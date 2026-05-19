import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';

import { MarketplaceHealthService } from './marketplace-health.service';
import { environment } from '../../../environments/environment';

describe('MarketplaceHealthService', () => {
  let service: MarketplaceHealthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [MarketplaceHealthService],
    });
    service = TestBed.inject(MarketplaceHealthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('list() GETs /marketplaces/health/', () => {
    service.list().subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/marketplaces/health/`);
    expect(req.request.method).toBe('GET');
    req.flush({
      items: [],
      order_poll_stale_minutes: 30,
      inbound_reconcile_stale_minutes: 90,
      webhook_disconnect_hours: 24,
    });
  });

  it('pollOrders(id) POSTs to the per-credential poll endpoint with an empty body', () => {
    service.pollOrders(42).subscribe();
    const req = httpMock.expectOne(
      `${environment.apiUrl}/marketplaces/health/42/poll-orders`,
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({});
    req.flush({
      credential_id: 42,
      marketplace_name: 'Amazon',
      orders_new: 0,
      orders_updated: 0,
      orders_skipped: 0,
      items_created: 0,
    });
  });

  it('reconcileInbound(id) POSTs to the per-credential reconcile endpoint', () => {
    service.reconcileInbound(7).subscribe();
    const req = httpMock.expectOne(
      `${environment.apiUrl}/marketplaces/health/7/reconcile-inbound`,
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({});
    req.flush({
      credential_id: 7,
      marketplace_name: 'MercadoLibre',
      transfers_processed: 0,
      transfers_updated: 0,
      total_received_added: 0,
      per_transfer: [],
    });
  });
});
