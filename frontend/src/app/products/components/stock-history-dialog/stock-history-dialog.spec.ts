import { ComponentFixture, TestBed } from '@angular/core/testing';
import { StockHistoryDialog, StockHistoryDialogData } from './stock-history-dialog';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { OrderByPipe } from '../../pipes/order-by.pipe';
import { DatePipe } from '@angular/common';

describe('StockHistoryDialog', () => {
    let component: StockHistoryDialog;
    let fixture: ComponentFixture<StockHistoryDialog>;
    let dialogRefMock: jasmine.SpyObj<MatDialogRef<StockHistoryDialog>>;

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
        dialogRefMock = jasmine.createSpyObj('MatDialogRef', ['close']);

        await TestBed.configureTestingModule({
            imports: [
                StockHistoryDialog,
                NoopAnimationsModule
            ],
            providers: [
                { provide: MatDialogRef, useValue: dialogRefMock },
                { provide: MAT_DIALOG_DATA, useValue: mockData },
                OrderByPipe,
                DatePipe
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(StockHistoryDialog);
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
        const emptyData = { ...mockData, inventoryAdjustments: [] };

        TestBed.configureTestingModule({
            imports: [StockHistoryDialog, NoopAnimationsModule],
            providers: [
                { provide: MatDialogRef, useValue: dialogRefMock },
                { provide: MAT_DIALOG_DATA, useValue: emptyData },
                OrderByPipe,
                DatePipe
            ]
        }).compileComponents();

        const emptyFixture = TestBed.createComponent(StockHistoryDialog);
        emptyFixture.detectChanges();
        const compiled = emptyFixture.nativeElement;

        expect(compiled.querySelector('.no-history')).toBeTruthy();
        expect(compiled.querySelectorAll('.adjustment-item').length).toBe(0);
    });

    it('should close dialog on close button click', () => {
        component.onClose();
        expect(dialogRefMock.close).toHaveBeenCalled();
    });
});
