import type { MockedObject } from 'vitest';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of } from 'rxjs';

import { StockTransferReconciliationComponent } from './stock-transfer-reconciliation';
import {
  ReconciliationRow,
  StockTransferService,
} from '../stock-transfer.service';

const sampleRows: ReconciliationRow[] = [
  {
    transfer_id: 1,
    transfer_status: 'received',
    dest_location: 'ml-full',
    product_id: 10,
    product_name: 'Widget',
    qty_shipped: 20,
    qty_received: 17,
    delta: -3,
  },
  {
    transfer_id: 2,
    transfer_status: 'received',
    dest_location: 'ml-full',
    product_id: 11,
    product_name: 'Gadget',
    qty_shipped: 5,
    qty_received: 6,
    delta: 1,
  },
];

describe('StockTransferReconciliationComponent', () => {
  let fixture: ComponentFixture<StockTransferReconciliationComponent>;
  let component: StockTransferReconciliationComponent;
  let service: MockedObject<StockTransferService>;

  beforeEach(async () => {
    const stub = {
      reconciliation: vi.fn().mockReturnValue(of(sampleRows)),
    };
    await TestBed.configureTestingModule({
      imports: [
        StockTransferReconciliationComponent,
        NoopAnimationsModule,
        RouterTestingModule,
        MatSnackBarModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [{ provide: StockTransferService, useValue: stub }],
    }).compileComponents();

    fixture = TestBed.createComponent(StockTransferReconciliationComponent);
    component = fixture.componentInstance;
    service = TestBed.inject(StockTransferService) as MockedObject<StockTransferService>;
    fixture.detectChanges();
  });

  it('loads reconciliation rows on init', () => {
    expect(service.reconciliation).toHaveBeenCalled();
    expect(component.rows.length).toBe(2);
  });

  it('sums delta across rows', () => {
    expect(component.totalDelta()).toBe(-2);
  });

  it('flags negative/positive deltas with distinct row classes', () => {
    expect(component.shrinkRowClass(sampleRows[0])).toBe('delta-negative');
    expect(component.shrinkRowClass(sampleRows[1])).toBe('delta-positive');
  });

  // --- Discrepancy tolerance (P2-5) ---------------------------------------

  function makeRow(over: Partial<ReconciliationRow>): ReconciliationRow {
    return {
      transfer_id: 1,
      transfer_status: 'received',
      dest_location: 'ml-full',
      product_id: 1,
      product_name: 'X',
      qty_shipped: 100,
      qty_received: 100,
      delta: 0,
      ...over,
    };
  }

  it('isDiscrepancy: a zero or within-tolerance delta is not flagged', () => {
    expect(component.isDiscrepancy(makeRow({ qty_received: 100, delta: 0 }))).toBe(false);
    // delta 3 on 100 = 3 units (≤10) and 3% (≤5%) → within tolerance
    expect(component.isDiscrepancy(makeRow({ qty_received: 97, delta: -3 }))).toBe(false);
  });

  it('isDiscrepancy: flags a large absolute OR large percent settled gap', () => {
    // delta -12 > 10 units → discrepancy
    expect(component.isDiscrepancy(makeRow({ qty_received: 88, delta: -12 }))).toBe(true);
    // delta -6 on 100 = 6% > 5% → discrepancy
    expect(component.isDiscrepancy(makeRow({ qty_received: 94, delta: -6 }))).toBe(true);
  });

  it('isDiscrepancy: an over-receipt counts in any state once out of tolerance', () => {
    expect(
      component.isDiscrepancy(
        makeRow({ transfer_status: 'partially_received', qty_shipped: 100, qty_received: 112, delta: 12 }),
      ),
    ).toBe(true);
  });

  it('isDiscrepancy: a shortfall on a still-receiving transfer is not yet settled', () => {
    // received < shipped on partially_received may simply be in transit
    expect(
      component.isDiscrepancy(
        makeRow({ transfer_status: 'partially_received', qty_shipped: 100, qty_received: 50, delta: -50 }),
      ),
    ).toBe(false);
    // but once RECEIVED, the same gap is a real shortfall
    expect(
      component.isDiscrepancy(
        makeRow({ transfer_status: 'received', qty_shipped: 100, qty_received: 50, delta: -50 }),
      ),
    ).toBe(true);
  });

  it('discrepancyLabel signs the delta', () => {
    expect(component.discrepancyLabel(makeRow({ delta: 12 }))).toBe('+12');
    expect(component.discrepancyLabel(makeRow({ delta: -15 }))).toBe('-15');
  });

  it('discrepancyCount tallies flagged rows', () => {
    component.rows = [
      makeRow({ qty_received: 100, delta: 0 }), // ok
      makeRow({ qty_received: 80, delta: -20 }), // flagged (abs)
      makeRow({ transfer_status: 'partially_received', qty_received: 60, delta: -40 }), // in transit, not flagged
    ];
    expect(component.discrepancyCount()).toBe(1);
  });
});
