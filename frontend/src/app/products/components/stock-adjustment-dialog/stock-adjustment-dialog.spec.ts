import { ComponentFixture, TestBed } from '@angular/core/testing';
import { StockAdjustmentDialog, StockAdjustmentData } from './stock-adjustment-dialog';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { FormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('StockAdjustmentDialog', () => {
  let component: StockAdjustmentDialog;
  let fixture: ComponentFixture<StockAdjustmentDialog>;
  let dialogRefMock: jasmine.SpyObj<MatDialogRef<StockAdjustmentDialog>>;

  const mockData: StockAdjustmentData = {
    productName: 'Test Product',
    currentQuantity: 10
  };

  beforeEach(async () => {
    dialogRefMock = jasmine.createSpyObj('MatDialogRef', ['close']);

    await TestBed.configureTestingModule({
      imports: [
        StockAdjustmentDialog,
        FormsModule,
        NoopAnimationsModule
      ],
      providers: [
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: mockData }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(StockAdjustmentDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize with data', () => {
    expect(component.data).toEqual(mockData);
    expect(component.adjustment).toBe(0);
    expect(component.showConfirmation).toBeFalse();
  });

  it('should show confirmation on confirmAdjustment if adjustment is valid', () => {
    component.adjustment = 5;
    component.confirmAdjustment();
    expect(component.showConfirmation).toBeTrue();
  });

  it('should not show confirmation if adjustment is 0', () => {
    component.adjustment = 0;
    component.confirmAdjustment();
    expect(component.showConfirmation).toBeFalse();
  });

  it('should close with result on confirmAndClose', () => {
    component.adjustment = 5;
    component.reason = 'Restock';
    component.confirmAndClose();
    expect(dialogRefMock.close).toHaveBeenCalledWith({ adjustment: 5, reason: 'Restock' });
  });

  it('should close without result on onCancel', () => {
    component.onCancel();
    expect(dialogRefMock.close).toHaveBeenCalledWith();
  });

  it('should reset confirmation on goBack', () => {
    component.showConfirmation = true;
    component.goBack();
    expect(component.showConfirmation).toBeFalse();
  });

  it('should reset confirmation on onAdjustmentChange', () => {
    component.showConfirmation = true;
    component.onAdjustmentChange();
    expect(component.showConfirmation).toBeFalse();
  });
});
