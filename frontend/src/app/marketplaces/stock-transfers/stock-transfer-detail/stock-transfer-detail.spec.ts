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
      reconcile: vi.fn().mockReturnValue(
        of({
          items_updated: 1,
          total_received_added: 3,
          status_before: 'shipped',
          status_after: 'partially_received',
          unmapped_listings: [],
          transfer: transfer({ status: 'partially_received' }),
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

  // -- Inbound reconciliation -------------------------------------------

  it('offers reconcile only for in-flight marketplace transfers with an external inbound id', () => {
    // DRAFT → not yet shipped → no reconcile.
    component.transfer = transfer({ status: 'draft' });
    expect(component.canReconcile()).toBe(false);

    // SHIPPED but no external_inbound_id (operator used manual workflow)
    // → still no reconcile button.
    component.transfer = transfer({ status: 'shipped', external_inbound_id: null });
    expect(component.canReconcile()).toBe(false);

    // SHIPPED + has external id → eligible.
    component.transfer = transfer({
      status: 'shipped',
      external_inbound_id: 'FBA-1',
      dest_location: 'amazon-fba',
    });
    expect(component.canReconcile()).toBe(true);

    // PARTIALLY_RECEIVED still eligible — we can pick up more.
    component.transfer = transfer({
      status: 'partially_received',
      external_inbound_id: 'FBA-1',
      dest_location: 'amazon-fba',
    });
    expect(component.canReconcile()).toBe(true);

    // RECEIVED → done, no more receipts expected.
    component.transfer = transfer({
      status: 'received',
      external_inbound_id: 'FBA-1',
      dest_location: 'amazon-fba',
    });
    expect(component.canReconcile()).toBe(false);

    // Non-marketplace destination → not applicable.
    component.transfer = transfer({
      status: 'shipped',
      external_inbound_id: 'X',
      dest_location: 'warehouse-b',
    });
    expect(component.canReconcile()).toBe(false);
  });

  it('reconcileNow() calls the service, refreshes the transfer, and records the result', () => {
    component.transfer = transfer({
      status: 'shipped',
      external_inbound_id: 'FBA-1',
      dest_location: 'amazon-fba',
    });
    component.reconcileNow();
    expect(service.reconcile).toHaveBeenCalledWith(42);
    expect(component.lastReconcile?.items_updated).toBe(1);
    expect(component.lastReconcile?.total_received_added).toBe(3);
    // The endpoint embeds the refreshed transfer so the UI doesn't
    // need a follow-up GET — the component should pick it up.
    expect(component.transfer?.status).toBe('partially_received');
  });

  it('reconcileNow() surfaces skipped/unmapped results without crashing', () => {
    service.reconcile.mockReturnValue(
      of({
        items_updated: 0,
        total_received_added: 0,
        status_before: 'shipped',
        status_after: 'shipped',
        skipped_reason: 'no_external_inbound_id',
        unmapped_listings: ['MLM-GHOST'],
        transfer: transfer({ status: 'shipped' }),
      }),
    );
    component.transfer = transfer({
      status: 'shipped',
      external_inbound_id: 'FBA-1',
      dest_location: 'amazon-fba',
    });
    component.reconcileNow();
    expect(component.lastReconcile?.skipped_reason).toBe('no_external_inbound_id');
    expect(component.lastReconcile?.unmapped_listings).toEqual(['MLM-GHOST']);
  });

  it('reconcileNow() is a no-op when no transfer is loaded or already acting', () => {
    component.transfer = null;
    component.reconcileNow();
    expect(service.reconcile).not.toHaveBeenCalled();

    component.transfer = transfer({
      status: 'shipped',
      external_inbound_id: 'FBA-1',
      dest_location: 'amazon-fba',
    });
    component.acting = true;
    component.reconcileNow();
    expect(service.reconcile).not.toHaveBeenCalled();
  });
});
