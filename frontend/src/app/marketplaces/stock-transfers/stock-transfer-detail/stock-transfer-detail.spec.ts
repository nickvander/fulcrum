import type { MockedObject } from 'vitest';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogModule } from '@angular/material/dialog';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of } from 'rxjs';

import { StockTransferDetailComponent } from './stock-transfer-detail';
import { StockTransfer, StockTransferService } from '../stock-transfer.service';

function transfer(overrides: Partial<StockTransfer> = {}): StockTransfer {
  return {
    id: 42,
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
        id: 1,
        transfer_id: 42,
        product_id: 7,
        variant_id: null,
        qty_planned: 8,
        qty_shipped: 0,
        qty_received: 0,
        product: { id: 7, name: 'Demo', sku: 'D-1' },
      },
    ],
    ...overrides,
  };
}

describe('StockTransferDetailComponent', () => {
  let fixture: ComponentFixture<StockTransferDetailComponent>;
  let component: StockTransferDetailComponent;
  let service: MockedObject<StockTransferService>;

  beforeEach(async () => {
    const stub = {
      get: vi.fn().mockReturnValue(of(transfer())),
      ship: vi.fn().mockReturnValue(of(transfer({ status: 'shipped' }))),
      cancel: vi.fn().mockReturnValue(of(transfer({ status: 'cancelled' }))),
      delete: vi.fn().mockReturnValue(of({ deleted: 42 })),
      syncListings: vi.fn().mockReturnValue(
        of({
          updated: [
            { product_id: 7, external_listing_id: 'MLM-1', qty: 8, ok: true },
          ],
          missing_listings: [],
        }),
      ),
    };

    await TestBed.configureTestingModule({
      imports: [
        StockTransferDetailComponent,
        NoopAnimationsModule,
        RouterTestingModule,
        MatDialogModule,
        MatSnackBarModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: StockTransferService, useValue: stub },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => '42' } } },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(StockTransferDetailComponent);
    component = fixture.componentInstance;
    service = TestBed.inject(StockTransferService) as MockedObject<StockTransferService>;
    fixture.detectChanges();
  });

  it('loads the transfer for the route id', () => {
    expect(service.get).toHaveBeenCalledWith(42);
    expect(component.transfer?.id).toBe(42);
  });

  it('exposes ship/receive/cancel/delete affordances based on status', () => {
    expect(component.canShip()).toBe(true);
    expect(component.canReceive()).toBe(false);
    expect(component.canCancel()).toBe(true);
    expect(component.canDelete()).toBe(true);

    component.transfer = transfer({ status: 'shipped' });
    expect(component.canShip()).toBe(false);
    expect(component.canReceive()).toBe(true);
    expect(component.canCancel()).toBe(false);
    expect(component.canDelete()).toBe(false);
  });

  it('ships the transfer when ship() is called', () => {
    component.ship();
    expect(service.ship).toHaveBeenCalledWith(42, false);
    expect(component.transfer?.status).toBe('shipped');
  });

  it('passes push_to_marketplace=true when ship(true) is called', () => {
    component.ship(true);
    expect(service.ship).toHaveBeenCalledWith(42, true);
  });

  it('only shows the sync action for marketplace destinations in received state', () => {
    component.transfer = transfer({ status: 'received' });
    expect(component.canSyncListings()).toBe(true);

    component.transfer = transfer({ status: 'received', dest_location: 'other' });
    expect(component.canSyncListings()).toBe(false);

    component.transfer = transfer({ status: 'draft' });
    expect(component.canSyncListings()).toBe(false);
  });

  it('records the last sync result and surfaces missing listings', () => {
    service.syncListings.mockReturnValue(
      of({
        updated: [],
        missing_listings: [{ product_id: 7, qty_to_publish: 4 }],
      }),
    );
    component.transfer = transfer({ status: 'received' });
    component.syncListings();
    expect(service.syncListings).toHaveBeenCalledWith(42);
    expect(component.lastSync?.missing_listings.length).toBe(1);
  });

  it('shows reauth state when the sync response says credentials are stale', () => {
    service.syncListings.mockReturnValue(
      of({
        updated: [
          { product_id: 7, external_listing_id: 'MLM-1', qty: 5, ok: false, error: 'needs_reauthorization' },
        ],
        missing_listings: [],
        needs_reauthorization: true,
        reauthorization_reason: 'refresh call failed: invalid_grant',
        marketplace: 'MercadoLibre',
      }),
    );
    component.transfer = transfer({ status: 'received' });
    component.syncListings();
    expect(component.lastSync?.needs_reauthorization).toBe(true);
    expect(component.lastSync?.marketplace).toBe('MercadoLibre');
  });
});
