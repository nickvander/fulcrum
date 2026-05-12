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
});
