import type { MockedObject } from 'vitest';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef } from '@angular/material/dialog';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of } from 'rxjs';

import { StockTransferCreateDialogComponent } from './stock-transfer-create-dialog';
import { ProductService } from '../../../products/services/product';
import {
  STOCK_LOCATION_INTERNAL,
  STOCK_LOCATION_ML_FULL,
  StockTransferService,
} from '../stock-transfer.service';

describe('StockTransferCreateDialogComponent', () => {
  let fixture: ComponentFixture<StockTransferCreateDialogComponent>;
  let component: StockTransferCreateDialogComponent;
  let service: MockedObject<StockTransferService>;
  let dialogRef: MockedObject<MatDialogRef<StockTransferCreateDialogComponent>>;

  beforeEach(async () => {
    const serviceStub = {
      create: vi.fn().mockReturnValue(of(null)),
    };
    const dialogRefStub = { close: vi.fn() };
    const productServiceStub = {
      getProducts: () =>
        of({
          data: [
            { id: 1, name: 'Tea', sku: 'TEA' },
            { id: 2, name: 'Coffee', sku: 'COF' },
          ],
        }),
    };

    await TestBed.configureTestingModule({
      imports: [
        StockTransferCreateDialogComponent,
        NoopAnimationsModule,
        MatSnackBarModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: StockTransferService, useValue: serviceStub },
        { provide: ProductService, useValue: productServiceStub },
        { provide: MatDialogRef, useValue: dialogRefStub },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(StockTransferCreateDialogComponent);
    component = fixture.componentInstance;
    service = TestBed.inject(StockTransferService) as MockedObject<StockTransferService>;
    dialogRef = TestBed.inject(MatDialogRef) as MockedObject<
      MatDialogRef<StockTransferCreateDialogComponent>
    >;
    fixture.detectChanges();
    // Make sure ngModel bindings settled before exercising state-dependent helpers.
    component.destLocation = STOCK_LOCATION_ML_FULL;
    component.sourceLocation = STOCK_LOCATION_INTERNAL;
  });

  it('loads products and filters out picked items', () => {
    expect(component.products.length).toBe(2);
    component.add(component.products[0]);
    expect(component.filteredProducts.map(p => p.id)).toEqual([2]);
  });

  it('filters by name and SKU', () => {
    component.search = 'tea';
    expect(component.filteredProducts.map(p => p.id)).toEqual([1]);

    component.search = 'cof';
    expect(component.filteredProducts.map(p => p.id)).toEqual([2]);
  });

  it('only enables save when there is at least one item with a positive qty', () => {
    expect(component.canSave()).toBe(false);
    component.add(component.products[0]);
    expect(component.canSave()).toBe(true);
    component.updateQty(component.selected[0], 0);
    expect(component.canSave()).toBe(false);
  });

  it('sends the create payload and closes with the new transfer', () => {
    const created = {
      id: 7,
      source_location: STOCK_LOCATION_INTERNAL,
      dest_location: STOCK_LOCATION_ML_FULL,
      status: 'draft' as const,
      notes: null,
      external_inbound_id: null,
      shipped_at: null,
      received_at: null,
      created_at: '',
      updated_at: '',
      items: [],
    };
    service.create.mockReturnValue(of(created));

    component.add(component.products[0]);
    component.updateQty(component.selected[0], 4);
    component.save();

    expect(service.create).toHaveBeenCalled();
    const payload = service.create.mock.calls[0][0];
    expect(payload.dest_location).toBe(STOCK_LOCATION_ML_FULL);
    expect(payload.items[0]).toEqual({ product_id: 1, qty_planned: 4 });
    expect(dialogRef.close).toHaveBeenCalledWith(created);
  });
});
