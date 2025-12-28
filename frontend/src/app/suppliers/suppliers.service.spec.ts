import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';

import { SuppliersService } from './suppliers.service';

describe('SuppliersService', () => {
  let service: SuppliersService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [SuppliersService]
    });
    service = TestBed.inject(SuppliersService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
