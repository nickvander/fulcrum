
import type { MockedObject } from "vitest";
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { StockHistoryDialogComponent, StockHistoryDialogData } from './stock-history-dialog.component';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { OrderByPipe } from '../../pipes/order-by.pipe';
import { DatePipe } from '@angular/common';
import { TranslocoTestingModule } from '@ngneat/transloco';

describe('StockHistoryDialogComponent', () => {
    let component: StockHistoryDialogComponent;
    let fixture: ComponentFixture<StockHistoryDialogComponent>;
    let dialogRefMock: MockedObject<MatDialogRef<StockHistoryDialogComponent>>;

    const mockData: StockHistoryDialogData = {
        productName: 'Test Product',
        currentStock: 100,
        inventoryAdjustments: [
            {
                id: 1,
                adjustment: 10,
                reason: 'Restock',
                timestamp: '2023-01-01T10:00:00Z',
                created_by: 'Admin'
            },
            {
                id: 2,
                adjustment: -5,
                reason: 'Damage',
                timestamp: '2023-01-02T10:00:00Z',
                created_by: 'User'
            }
        ]
    };

    beforeEach(async () => {
        dialogRefMock = {
            close: vi.fn().mockName("MatDialogRef.close")
        } as any;

        await TestBed.configureTestingModule({
            imports: [
        TranslocoTestingModule.forRoot({ langs: { en: {}, 'es-MX': {} } }),
                StockHistoryDialogComponent,
                NoopAnimationsModule
            ],
            providers: [
                { provide: MatDialogRef, useValue: dialogRefMock },
                { provide: MAT_DIALOG_DATA, useValue: mockData },
                OrderByPipe,
                DatePipe
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(StockHistoryDialogComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should initialize with data', () => {
        expect(component.data).toEqual(mockData);
    });

    it('should display history items', () => {
        const compiled = fixture.nativeElement;
        const items = compiled.querySelectorAll('.adjustment-item');
        expect(items.length).toBe(2);
    });

    it('should display no history message when adjustments are empty', () => {
        TestBed.resetTestingModule();
        const emptyData = { ...mockData, inventoryAdjustments: [] } as any;

        TestBed.configureTestingModule({
            imports: [
                TranslocoTestingModule.forRoot({ langs: { en: {}, 'es-MX': {} } }),
                StockHistoryDialogComponent,
                NoopAnimationsModule,
            ],
            providers: [
                { provide: MatDialogRef, useValue: dialogRefMock },
                { provide: MAT_DIALOG_DATA, useValue: emptyData },
                OrderByPipe,
                DatePipe
            ]
        }).compileComponents();

        const emptyFixture = TestBed.createComponent(StockHistoryDialogComponent);
        emptyFixture.detectChanges();
        const compiled = emptyFixture.nativeElement;

        expect(compiled.querySelector('.no-history')).toBeTruthy();
        expect(compiled.querySelectorAll('.adjustment-item').length).toBe(0);
    });

    it('should close dialog on close button click', () => {
        component.onClose();
        expect(dialogRefMock.close).toHaveBeenCalled();
    });

    describe('structured origin chip', () => {
        const base = { id: 9, adjustment: 5, timestamp: 't', created_by: 'a', reason: null as string | null };

        it('resolves a purchase_order origin with a PO deep-link', () => {
            const o = component.origin({ ...base, reason: 'Received PO #42', source: 'purchase_order', source_id: 42 });
            expect(o).toEqual({
                labelKey: 'products.stockHistoryDialog.receivedPo',
                id: 42,
                commands: ['/suppliers/po', 42],
            });
        });

        it('does NOT depend on the reason string for structured rows', () => {
            // A localized / unexpected reason must not affect the origin when
            // the structured source is present — the whole point of P1-9/P2-8.
            const o = component.origin({ ...base, reason: 'texto localizado', source: 'purchase_order', source_id: 7 });
            expect(o?.commands).toEqual(['/suppliers/po', 7]);
        });

        it('links transfers, orders, and counts to their detail routes', () => {
            expect(component.origin({ ...base, source: 'stock_transfer', source_id: 3 })?.commands).toEqual(['/marketplaces/transfers', 3]);
            expect(component.origin({ ...base, source: 'sales_order', source_id: 8 })?.commands).toEqual(['/orders', 8]);
            expect(component.origin({ ...base, source: 'inventory_count', source_id: 5 })?.commands).toEqual(['/inventory/count', 5]);
        });

        it('shows non-linkable origins as a plain labelled chip', () => {
            const bundle = component.origin({ ...base, source: 'bundle_assembly', source_id: 12 });
            expect(bundle).toEqual({ labelKey: 'products.stockHistoryDialog.fromBundle', id: 12, commands: null });
            const reversal = component.origin({ ...base, source: 'adjustment_reversal', source_id: 4 });
            expect(reversal?.commands).toBeNull();
            const sync = component.origin({ ...base, source: 'marketplace_sync', source_id: null });
            expect(sync).toEqual({ labelKey: 'products.stockHistoryDialog.fromMarketplaceSync', id: null, commands: null });
        });

        it('falls back to the legacy English PO reason when source is absent', () => {
            const o = component.origin({ ...base, reason: 'Received PO #13', source: null, source_id: null });
            expect(o?.commands).toEqual(['/suppliers/po', 13]);
        });

        it('treats a plain manual adjustment as reason-only (no origin)', () => {
            expect(component.origin({ ...base, reason: 'Damage', source: null, source_id: null })).toBeNull();
        });

        it('does not linkify a non-PO source just because the reason looks like a PO', () => {
            // structured source wins: a transfer row whose free-text happens to
            // start with the English PO prefix still routes to the transfer.
            const o = component.origin({ ...base, reason: 'Received PO #99 (note)', source: 'stock_transfer', source_id: 3 });
            expect(o?.commands).toEqual(['/marketplaces/transfers', 3]);
        });

        it('returns null for an unknown/future source (renders plain reason)', () => {
            expect(component.origin({ ...base, reason: 'x', source: 'something_new', source_id: 1 })).toBeNull();
        });

        it('navigates via the resolved origin commands and closes the dialog', () => {
            const navigate = vi.fn();
            (component as any).router = { navigate };
            component.goToOrigin({ labelKey: 'k', id: 55, commands: ['/orders', 55] });
            expect(dialogRefMock.close).toHaveBeenCalled();
            expect(navigate).toHaveBeenCalledWith(['/orders', 55]);
        });

        it('goToOrigin is a no-op for a non-linkable origin', () => {
            const navigate = vi.fn();
            (component as any).router = { navigate };
            component.goToOrigin({ labelKey: 'k', id: 1, commands: null });
            expect(navigate).not.toHaveBeenCalled();
        });
    });
});
