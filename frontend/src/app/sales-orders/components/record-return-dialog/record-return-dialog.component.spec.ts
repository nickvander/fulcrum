import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { RecordReturnDialogComponent, RecordReturnDialogData } from './record-return-dialog.component';
import { SalesOrdersService, SalesOrderDetail } from '../../services/sales-orders.service';

const ORDER: SalesOrderDetail = {
  id: 100,
  status: 'PAID',
  total_price: 210,
  created_at: '2026-05-01T10:00:00Z',
  source: 'MERCADOLIBRE',
  external_order_id: 'EXT-100',
  items: [
    { id: 11, product_id: 1, quantity: 2, price_per_unit: 50, product_name: 'A', product_sku: 'A-1' },
    { id: 12, product_id: 2, quantity: 3, price_per_unit: 80, product_name: 'B', product_sku: 'B-1' },
  ],
};

describe('RecordReturnDialogComponent', () => {
  let fixture: ComponentFixture<RecordReturnDialogComponent>;
  let component: RecordReturnDialogComponent;
  let salesOrdersStub: { recordReturn: ReturnType<typeof vi.fn> };
  let dialogRefStub: { close: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    salesOrdersStub = { recordReturn: vi.fn().mockReturnValue(of([])) };
    dialogRefStub = { close: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [
        RecordReturnDialogComponent,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: { order: ORDER } as RecordReturnDialogData },
        { provide: MatDialogRef, useValue: dialogRefStub },
        { provide: SalesOrdersService, useValue: salesOrdersStub },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(RecordReturnDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('builds one editable row per order item, defaulting quantity to the ordered qty', () => {
    expect(component.lines).toHaveLength(2);
    expect(component.lines[0].quantity).toBe(2);
    expect(component.lines[1].quantity).toBe(3);
    // None pre-selected — opt-in safer than opt-out.
    expect(component.lines.every(l => !l.selected)).toBe(true);
  });

  it('canSubmit() is false when no line is selected', () => {
    expect(component.canSubmit()).toBe(false);
  });

  it('canSubmit() flips true once at least one line is checked', () => {
    component.lines[0].selected = true;
    expect(component.canSubmit()).toBe(true);
  });

  it('submit() sends only selected lines with their per-row quantity', () => {
    component.lines[0].selected = true;
    component.lines[0].quantity = 1;  // partial return
    component.reason = 'damaged';
    component.notes = 'box was crushed';

    component.submit();

    expect(salesOrdersStub.recordReturn).toHaveBeenCalledTimes(1);
    const [orderId, payload] = salesOrdersStub.recordReturn.mock.calls[0];
    expect(orderId).toBe(100);
    expect(payload.lines).toEqual([{ order_item_id: 11, quantity: 1 }]);
    expect(payload.reason).toBe('damaged');
    expect(payload.notes).toBe('box was crushed');
  });

  it('submit() closes the dialog with the created rows on success', () => {
    component.lines[0].selected = true;
    salesOrdersStub.recordReturn.mockReturnValue(of([
      { id: 99, order_id: 100, order_item_id: 11, product_id: 1, quantity: 2, received_at: '2026-05-19T00:00:00Z' },
    ]));
    component.submit();
    expect(dialogRefStub.close).toHaveBeenCalledWith({
      created: expect.any(Array),
    });
    const call = dialogRefStub.close.mock.calls[0][0];
    expect(call.created).toHaveLength(1);
    expect(call.created[0].id).toBe(99);
  });

  it('submit() surfaces the error message and keeps the dialog open on failure', () => {
    component.lines[0].selected = true;
    salesOrdersStub.recordReturn.mockReturnValue(
      throwError(() => ({ error: { detail: 'item not in order' } })),
    );
    component.submit();
    expect(component.errorMessage).toBe('item not in order');
    expect(dialogRefStub.close).not.toHaveBeenCalled();
    expect(component.saving).toBe(false);
  });

  it('cancel() closes the dialog with null', () => {
    component.cancel();
    expect(dialogRefStub.close).toHaveBeenCalledWith(null);
  });

  it('renders one checkbox row per line item', () => {
    expect(fixture.debugElement.queryAll(By.css('.line-row'))).toHaveLength(2);
    expect(fixture.debugElement.query(By.css('[data-testid="record-return-line-11"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="record-return-line-12"]'))).not.toBeNull();
  });
});
