import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { InvoiceMatchDialogComponent, InvoiceMatchDialogData } from './invoice-match-dialog.component';

describe('InvoiceMatchDialogComponent', () => {
  let component: InvoiceMatchDialogComponent;
  let fixture: ComponentFixture<InvoiceMatchDialogComponent>;
  let dialogRef: { close: ReturnType<typeof vi.fn> };

  const data: InvoiceMatchDialogData = {
    poId: 42,
    matchResult: {
      invoice_number: 'INV-1',
      invoice_date: '2026-05-10',
      vendor_name: 'Alibaba Supplier',
      matches: [
        {
          po_item_id: 10,
          po_description: 'Widget',
          po_quantity: 12,
          po_quantity_received: 5,
          po_remaining_quantity: 7,
          po_unit_cost: 4,
          invoice_sku: 'W-1',
          invoice_description: 'Widget',
          invoice_quantity: 10,
          invoice_unit_cost: 4,
          invoice_line_total: 40,
          match_status: 'matched',
          confidence: 1,
          discrepancy_details: null
        },
        {
          po_item_id: 11,
          po_description: 'Complete Widget',
          po_quantity: 3,
          po_quantity_received: 3,
          po_remaining_quantity: 0,
          po_unit_cost: 8,
          invoice_sku: 'W-2',
          invoice_description: 'Complete Widget',
          invoice_quantity: 3,
          invoice_unit_cost: 8,
          invoice_line_total: 24,
          match_status: 'matched',
          confidence: 1,
          discrepancy_details: null
        }
      ],
      unmatched_po_items: [],
      unmatched_invoice_items: [],
      total_discrepancy: 0,
      overall_confidence: 1,
      extraction_confidence: 1
    }
  };

  beforeEach(async () => {
    dialogRef = { close: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [
        InvoiceMatchDialogComponent,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({ langs: { en: {}, 'es-MX': {} } })
      ],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: structuredClone(data) },
        { provide: MatDialogRef, useValue: dialogRef }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(InvoiceMatchDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('defaults receive quantities to the lesser of invoice quantity and PO remaining quantity', () => {
    expect(component.data.matchResult.matches[0].receive_quantity).toBe(7);
    expect(component.data.matchResult.matches[1].receive_quantity).toBe(0);
    expect(component.getReceivableMatchCount()).toBe(1);
  });

  it('clamps edited receive quantities to PO remaining quantity', () => {
    const item = component.data.matchResult.matches[0];
    item.receive_quantity = 99;

    component.clampReceiveQuantity(item);

    expect(item.receive_quantity).toBe(7);
  });

  it('returns edited receive quantities when receiving matched stock', () => {
    component.data.matchResult.matches[0].receive_quantity = 3;

    component.receiveMatchedItems();

    expect(dialogRef.close).toHaveBeenCalledWith({
      action: 'receive',
      matchResult: component.data.matchResult
    });
  });
});
