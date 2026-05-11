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
                BrowserAnimationsModule
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
        expect(dialogRefMock.close).toHaveBeenCalled();
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
