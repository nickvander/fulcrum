import type { MockedObject } from 'vitest';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialogModule } from '@angular/material/dialog';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { StockTransferListComponent } from './stock-transfer-list';
import { StockTransfer, StockTransferService } from '../stock-transfer.service';

const sampleTransfer: StockTransfer = {
  id: 1,
  source_location: 'default',
  dest_location: 'ml-full',
  status: 'draft',
  notes: null,
  external_inbound_id: null,
  shipped_at: null,
  received_at: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  items: [
    {
      id: 10,
      transfer_id: 1,
      product_id: 99,
      variant_id: null,
      qty_planned: 5,
      qty_shipped: 0,
      qty_received: 0,
      product: { id: 99, name: 'Sample', sku: 'SAMPLE' },
    },
  ],
};

describe('StockTransferListComponent', () => {
  let fixture: ComponentFixture<StockTransferListComponent>;
  let component: StockTransferListComponent;
  let service: MockedObject<StockTransferService>;

  beforeEach(async () => {
    const stub = {
      list: vi.fn().mockReturnValue(of([sampleTransfer])),
    };

    await TestBed.configureTestingModule({
      imports: [
        StockTransferListComponent,
        NoopAnimationsModule,
        RouterTestingModule,
        MatSnackBarModule,
        MatDialogModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: StockTransferService, useValue: stub },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => null } } },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(StockTransferListComponent);
    component = fixture.componentInstance;
    service = TestBed.inject(StockTransferService) as MockedObject<StockTransferService>;
    fixture.detectChanges();
  });

  it('loads transfers on init', () => {
    expect(service.list).toHaveBeenCalled();
    expect(component.transfers.length).toBe(1);
    expect(component.transfers[0].id).toBe(1);
  });

  it('refetches with a status filter when a tab is switched', () => {
    service.list.mockClear();
    service.list.mockReturnValue(of([]));
    component.onFilterChange(1); // draft
    expect(service.list).toHaveBeenCalledWith('draft');
  });

  it('summarises planned and received units', () => {
    expect(component.unitsPlanned(sampleTransfer)).toBe(5);
    expect(component.unitsReceived(sampleTransfer)).toBe(0);
  });

  it('surfaces an error from the list call without crashing', () => {
    service.list.mockReturnValue(throwError(() => new Error('boom')));
    component.reload();
    expect(component.loading).toBe(false);
    expect(component.transfers.length).toBe(1); // previous state retained
  });
});
