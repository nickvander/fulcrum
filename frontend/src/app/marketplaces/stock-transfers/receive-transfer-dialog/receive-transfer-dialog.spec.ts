import type { MockedObject } from 'vitest';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of } from 'rxjs';

import { ReceiveTransferDialogComponent } from './receive-transfer-dialog';
import { StockTransfer, StockTransferService } from '../stock-transfer.service';

function transferWithShipped(): StockTransfer {
  return {
    id: 9,
    source_location: 'default',
    dest_location: 'ml-full',
    status: 'shipped',
    notes: null,
    external_inbound_id: null,
    shipped_at: null,
    received_at: null,
    created_at: '',
    updated_at: '',
    items: [
      {
        id: 100,
        transfer_id: 9,
        product_id: 5,
        variant_id: null,
        qty_planned: 10,
        qty_shipped: 10,
        qty_received: 3,
        product: { id: 5, name: 'Mug', sku: 'MUG' },
      },
    ],
  };
}

describe('ReceiveTransferDialogComponent', () => {
  let fixture: ComponentFixture<ReceiveTransferDialogComponent>;
  let component: ReceiveTransferDialogComponent;
  let service: MockedObject<StockTransferService>;
  let dialogRef: MockedObject<MatDialogRef<ReceiveTransferDialogComponent>>;

  beforeEach(async () => {
    const serviceStub = {
      receive: vi.fn().mockReturnValue(of(null)),
    };
    const dialogRefStub = { close: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [
        ReceiveTransferDialogComponent,
        NoopAnimationsModule,
        MatSnackBarModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: StockTransferService, useValue: serviceStub },
        { provide: MatDialogRef, useValue: dialogRefStub },
        { provide: MAT_DIALOG_DATA, useValue: { transfer: transferWithShipped() } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ReceiveTransferDialogComponent);
    component = fixture.componentInstance;
    service = TestBed.inject(StockTransferService) as MockedObject<StockTransferService>;
    dialogRef = TestBed.inject(MatDialogRef) as MockedObject<
      MatDialogRef<ReceiveTransferDialogComponent>
    >;
    fixture.detectChanges();
  });

  it('defaults receive quantities to the remaining shipped amount', () => {
    expect(component.rows[0].remaining).toBe(7);
    expect(component.rows[0].toReceive).toBe(7);
  });

  it('clamps to-receive at the remaining amount', () => {
    component.updateToReceive(component.rows[0], 999);
    expect(component.rows[0].toReceive).toBe(7);
    component.updateToReceive(component.rows[0], -3);
    expect(component.rows[0].toReceive).toBe(0);
  });

  it('only allows save when at least one row has a positive quantity', () => {
    expect(component.canSave()).toBe(true);
    component.updateToReceive(component.rows[0], 0);
    expect(component.canSave()).toBe(false);
  });

  it('submits the receive payload and closes the dialog', () => {
    const updated = transferWithShipped();
    updated.status = 'received';
    service.receive.mockReturnValue(of(updated));

    component.save();

    expect(service.receive).toHaveBeenCalled();
    const [id, lines] = service.receive.mock.calls[0];
    expect(id).toBe(9);
    expect(lines[0]).toEqual({ transfer_item_id: 100, product_id: 5, quantity: 7 });
    expect(dialogRef.close).toHaveBeenCalledWith(updated);
  });
});
