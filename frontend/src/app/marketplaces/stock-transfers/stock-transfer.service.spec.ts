import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import {
  STOCK_LOCATION_INTERNAL,
  STOCK_LOCATION_ML_FULL,
  StockTransferService,
} from './stock-transfer.service';

describe('StockTransferService', () => {
  let service: StockTransferService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [StockTransferService],
    });
    service = TestBed.inject(StockTransferService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('lists transfers, passing the status filter through as a query param', () => {
    service.list('draft').subscribe();
    const req = httpMock.expectOne(r => r.url === '/api/v1/stock-transfers/');
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('status')).toBe('draft');
    req.flush([]);
  });

  it('omits the status param when no filter is given', () => {
    service.list(null).subscribe();
    const req = httpMock.expectOne(r => r.url === '/api/v1/stock-transfers/');
    expect(req.request.params.has('status')).toBe(false);
    req.flush([]);
  });

  it('creates a transfer with the provided destination and items', () => {
    service
      .create({
        source_location: STOCK_LOCATION_INTERNAL,
        dest_location: STOCK_LOCATION_ML_FULL,
        items: [{ product_id: 7, qty_planned: 5 }],
      })
      .subscribe();
    const req = httpMock.expectOne('/api/v1/stock-transfers/');
    expect(req.request.method).toBe('POST');
    expect(req.request.body.dest_location).toBe(STOCK_LOCATION_ML_FULL);
    expect(req.request.body.items[0]).toEqual({ product_id: 7, qty_planned: 5 });
    req.flush({ id: 11 });
  });

  it('posts ship and receive to the right endpoints', () => {
    service.ship(3).subscribe();
    const ship = httpMock.expectOne(r => r.url === '/api/v1/stock-transfers/3/ship');
    expect(ship.request.params.has('push_to_marketplace')).toBe(false);
    ship.flush({});

    service.receive(3, [{ product_id: 1, quantity: 2 }]).subscribe();
    const recv = httpMock.expectOne('/api/v1/stock-transfers/3/receive');
    expect(recv.request.body[0]).toEqual({ product_id: 1, quantity: 2 });
    recv.flush({});
  });

  it('attaches push_to_marketplace=true to ship when requested', () => {
    service.ship(5, true).subscribe();
    const req = httpMock.expectOne(r => r.url === '/api/v1/stock-transfers/5/ship');
    expect(req.request.params.get('push_to_marketplace')).toBe('true');
    req.flush({});
  });

  it('calls the sync-listings endpoint', () => {
    service.syncListings(11).subscribe();
    const req = httpMock.expectOne('/api/v1/stock-transfers/11/sync-listings');
    expect(req.request.method).toBe('POST');
    req.flush({ updated: [], missing_listings: [] });
  });

  it('fetches the inventory snapshot from the planner endpoint', () => {
    service.inventorySnapshot().subscribe();
    const req = httpMock.expectOne('/api/v1/stock-transfers/inventory-snapshot');
    expect(req.request.method).toBe('GET');
    req.flush([]);
  });

  it('plans allocations with notes', () => {
    service
      .planAllocations(
        [{ product_id: 1, dest_location: 'ml-full', qty_planned: 5 }],
        'first',
      )
      .subscribe();
    const req = httpMock.expectOne('/api/v1/stock-transfers/plan-allocations');
    expect(req.request.method).toBe('POST');
    expect(req.request.body.allocations.length).toBe(1);
    expect(req.request.body.notes).toBe('first');
    req.flush([]);
  });

  it('fetches the reconciliation report', () => {
    service.reconciliation().subscribe();
    const req = httpMock.expectOne('/api/v1/stock-transfers/reconciliation');
    expect(req.request.method).toBe('GET');
    req.flush([]);
  });
});
