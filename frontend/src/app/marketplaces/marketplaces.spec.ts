import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';

import { MarketplacesService } from './marketplaces';
import { environment } from '../../environments/environment';

describe('MarketplacesService', () => {
  let service: MarketplacesService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [MarketplacesService],
    });
    service = TestBed.inject(MarketplacesService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('getMarketplaceById(id) GETs /marketplace/{id}', () => {
    service.getMarketplaceById(7).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/marketplace/7`);
    expect(req.request.method).toBe('GET');
    req.flush({ id: 7, name: 'Amazon' });
  });

  it('updateFeeConfig() PATCHes /marketplace/{id}/fee-config with the partial body', () => {
    service.updateFeeConfig(3, { default_fee_rate: 0.12 }).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/marketplace/3/fee-config`);
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ default_fee_rate: 0.12 });
    req.flush({ id: 3, name: 'Amazon', default_fee_rate: 0.12 });
  });

  it('recomputeCostBreakdowns() POSTs /marketplace/{id}/recompute-cost-breakdowns', () => {
    service.recomputeCostBreakdowns(9).subscribe();
    const req = httpMock.expectOne(
      `${environment.apiUrl}/marketplace/9/recompute-cost-breakdowns`,
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({});
    req.flush({ breakdowns_created: 0, breakdowns_updated: 0, errors: 0 });
  });
});
