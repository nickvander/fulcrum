import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReceivingDialogComponent } from './receiving-dialog.component';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { SuppliersService } from '../../suppliers.service';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { of } from 'rxjs';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { vi } from 'vitest';
import { CommonModule } from '@angular/common';
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { getTranslocoTestingModule } from '../../../testing/transloco-testing';

describe('ReceivingDialogComponent', () => {
    let component: ReceivingDialogComponent;
    let fixture: ComponentFixture<ReceivingDialogComponent>;
    let suppliersServiceMock: any;
    let dialogRefMock: any;

    const mockPO = {
        id: 1,
        items: [
            { id: 11, product_id: 101, variant_id: null, quantity_ordered: 10, quantity_received: 5 }
        ]
    };

    beforeEach(async () => {
        suppliersServiceMock = {
            receivePurchaseOrderItems: vi.fn(),
            correctReceivedPurchaseOrderItems: vi.fn()
        };
        dialogRefMock = {
            close: vi.fn()
        };

        await TestBed.configureTestingModule({
            declarations: [],
            imports: [
                ReceivingDialogComponent,
                CommonModule,
                ReactiveFormsModule,
                MatDialogModule,
                MatFormFieldModule,
                MatInputModule,
                MatButtonModule,
                BrowserAnimationsModule,
                getTranslocoTestingModule()
            ],
            providers: [
                FormBuilder,
                { provide: MAT_DIALOG_DATA, useValue: { po: mockPO } },
                { provide: MatDialogRef, useValue: dialogRefMock },
                { provide: SuppliersService, useValue: suppliersServiceMock }
            ],
            schemas: [CUSTOM_ELEMENTS_SCHEMA]
        })
            .compileComponents();

        fixture = TestBed.createComponent(ReceivingDialogComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should initialize items array', () => {
        expect(component.items.length).toBe(1);
        expect(component.items.at(0).get('quantity_to_receive')?.value).toBe(5); // 10 ordered - 5 received
    });

    it('should submit receiving items', () => {
        component.items.at(0).patchValue({ quantity_to_receive: 2 });
        suppliersServiceMock.receivePurchaseOrderItems.mockReturnValue(of({} as any));

        component.onSubmit();
        expect(suppliersServiceMock.receivePurchaseOrderItems).toHaveBeenCalledWith(1, [
            { po_item_id: 11, product_id: 101, variant_id: null, quantity: 2 }
        ]);
        // Closes with a rich payload so the opener can show success + Undo.
        const payload = dialogRefMock.close.mock.calls[0][0];
        expect(payload.po).toBeDefined();
        expect(payload.total).toBe(2);
        expect(payload.receivedItems).toHaveLength(1);
        expect(payload.destinationKey).toBe('products.bucketDefault');
    });

    it('applyScannedCode matches a line by SKU and bumps its receive qty', () => {
        (component.po.items[0] as any).product = { sku: 'ABC-1', barcode_value: '7501234567890' };
        const before = component.items.at(0).get('quantity_to_receive')?.value;

        const matched = component.applyScannedCode('abc-1'); // case-insensitive

        expect(matched).toBe(true);
        expect(component.items.at(0).get('quantity_to_receive')?.value).toBe(before + 1);
    });

    it('applyScannedCode matches by barcode too', () => {
        (component.po.items[0] as any).product = { sku: 'ABC-1', barcode_value: '7501234567890' };
        expect(component.applyScannedCode('7501234567890')).toBe(true);
    });

    it('applyScannedCode returns false when nothing matches', () => {
        (component.po.items[0] as any).product = { sku: 'ABC-1' };
        const before = component.items.at(0).get('quantity_to_receive')?.value;
        expect(component.applyScannedCode('ZZZ-999')).toBe(false);
        expect(component.items.at(0).get('quantity_to_receive')?.value).toBe(before);
    });

    it('should submit receiving corrections in correction mode', () => {
        component.mode = 'correct';
        component.receivingForm.patchValue({ reason: 'Counted twice' });
        component.items.at(0).patchValue({ quantity_to_receive: 2 });
        suppliersServiceMock.correctReceivedPurchaseOrderItems.mockReturnValue(of({} as any));

        component.onSubmit();

        expect(suppliersServiceMock.correctReceivedPurchaseOrderItems).toHaveBeenCalledWith(1, [
            { po_item_id: 11, product_id: 101, variant_id: null, quantity: 2, reason: 'Counted twice' }
        ]);
        expect(dialogRefMock.close).toHaveBeenCalled();
    });
});
