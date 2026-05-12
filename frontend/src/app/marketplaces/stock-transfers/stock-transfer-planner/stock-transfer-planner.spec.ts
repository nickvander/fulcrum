import type { MockedObject } from 'vitest';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of } from 'rxjs';

import { StockTransferPlannerComponent } from './stock-transfer-planner';
import {
  InventorySnapshotRow,
  STOCK_LOCATION_AMAZON_FBA,
  STOCK_LOCATION_INTERNAL,
  STOCK_LOCATION_ML_FULL,
  StockTransferService,
} from '../stock-transfer.service';

function snapshotRow(overrides: Partial<InventorySnapshotRow> = {}): InventorySnapshotRow {
  return {
    product_id: 1,
    product_name: 'Widget',
    product_sku: 'WIDGET-1',
    by_location: {
      [STOCK_LOCATION_INTERNAL]: 100,
      [STOCK_LOCATION_ML_FULL]: 0,
      [STOCK_LOCATION_AMAZON_FBA]: 0,
    },
    total: 100,
    ...overrides,
  };
}

describe('StockTransferPlannerComponent', () => {
  let fixture: ComponentFixture<StockTransferPlannerComponent>;
  let component: StockTransferPlannerComponent;
  let service: MockedObject<StockTransferService>;

  beforeEach(async () => {
    const stub = {
      inventorySnapshot: vi
        .fn()
        .mockReturnValue(
          of([
            snapshotRow(),
            snapshotRow({ product_id: 2, product_name: 'Gadget', product_sku: 'GADGET-2' }),
          ]),
        ),
      planAllocations: vi.fn().mockReturnValue(of([])),
    };
    await TestBed.configureTestingModule({
      imports: [
        StockTransferPlannerComponent,
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

    fixture = TestBed.createComponent(StockTransferPlannerComponent);
    component = fixture.componentInstance;
    service = TestBed.inject(StockTransferService) as MockedObject<StockTransferService>;
    fixture.detectChanges();
  });

  it('loads the inventory snapshot on init', () => {
    expect(service.inventorySnapshot).toHaveBeenCalled();
    expect(component.rows.length).toBe(2);
    expect(component.rows[0].internal).toBe(100);
  });

  it('flags over-allocation when ML + Amazon exceed internal stock', () => {
    const row = component.rows[0];
    component.updateAlloc(row, 'allocateMl', 70);
    component.updateAlloc(row, 'allocateAmazon', 40);
    expect(component.remaining(row)).toBe(-10);
    expect(component.isOver(row)).toBe(true);
    expect(component.canSave()).toBe(false);
  });

  it('allows save once allocations are within stock', () => {
    const row = component.rows[0];
    component.updateAlloc(row, 'allocateMl', 30);
    component.updateAlloc(row, 'allocateAmazon', 20);
    expect(component.canSave()).toBe(true);
  });

  it('submits one allocation per non-zero destination', () => {
    const a = component.rows[0];
    const b = component.rows[1];
    component.updateAlloc(a, 'allocateMl', 25);
    component.updateAlloc(b, 'allocateAmazon', 10);
    component.notes = 'Planner notes';
    component.save();

    expect(service.planAllocations).toHaveBeenCalled();
    const [allocations, notes] = service.planAllocations.mock.calls[0];
    expect(notes).toBe('Planner notes');
    expect(allocations).toEqual([
      { product_id: a.productId, dest_location: STOCK_LOCATION_ML_FULL, qty_planned: 25 },
      { product_id: b.productId, dest_location: STOCK_LOCATION_AMAZON_FBA, qty_planned: 10 },
    ]);
  });

  it('filters rows by name or SKU', () => {
    component.search = 'gadget';
    expect(component.filteredRows.map(r => r.productName)).toEqual(['Gadget']);

    component.search = 'widget-1';
    expect(component.filteredRows.length).toBe(1);
  });
});
