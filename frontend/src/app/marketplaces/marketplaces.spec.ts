import { TestBed } from '@angular/core/testing';

import { MarketplacesService } from './marketplaces';

describe('MarketplacesService', () => {
  let service: MarketplacesService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [MarketplacesService]
    });
    service = TestBed.inject(MarketplacesService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
