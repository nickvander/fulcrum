import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { FormsModule } from '@angular/forms';

import { StockAdjustmentDialog } from './stock-adjustment-dialog';

xdescribe('StockAdjustmentDialog', () => {
  let component: StockAdjustmentDialog;
  let fixture: ComponentFixture<StockAdjustmentDialog>;
  let mockDialogRef: jasmine.SpyObj<MatDialogRef<StockAdjustmentDialog>>;
  const mockDialogData = {
    productName: 'Test Product',
    currentQuantity: 5
  };

  beforeEach(async () => {
    mockDialogRef = jasmine.createSpyObj('MatDialogRef', ['close']);

    await TestBed.configureTestingModule({
      imports: [StockAdjustmentDialog, NoopAnimationsModule, FormsModule],
      providers: [
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: mockDialogData },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(StockAdjustmentDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize with default adjustment value of 0', () => {
    expect(component.adjustment).toBe(0);
  });

  it('should display product name and current quantity from dialog data', () => {
    // Create a fresh component to test the template
    const freshFixture = TestBed.createComponent(StockAdjustmentDialog);
    const freshComponent = freshFixture.componentInstance;
    freshFixture.detectChanges();
    
    const compiled = freshFixture.nativeElement;
    expect(compiled.querySelector('h2').textContent).toContain('Adjust Stock for Test Product');
    expect(compiled.textContent).toContain('Current Stock: 5');
  });

  it('should update adjustment value when input changes', async () => {
    const inputElement = fixture.nativeElement.querySelector('input');
    inputElement.value = '10';
    inputElement.dispatchEvent(new Event('input'));
    
    fixture.detectChanges();
    await fixture.whenStable();
    
    expect(component.adjustment).toBe(10);
  });

  it('should close dialog with adjustment value when confirm button is clicked', () => {
    component.adjustment = 10;
    
    const confirmButton = fixture.nativeElement.querySelectorAll('button')[1]; // Second button is confirm
    confirmButton.click();
    
    expect(mockDialogRef.close).toHaveBeenCalledWith(10);
  });

  it('should close dialog without value when cancel button is clicked', () => {
    component.adjustment = 10;
    
    const cancelButton = fixture.nativeElement.querySelector('button'); // First button is cancel
    cancelButton.click();
    
    expect(mockDialogRef.close).toHaveBeenCalledWith();
  });

  it('should handle negative adjustments correctly', async () => {
    const inputElement = fixture.nativeElement.querySelector('input');
    inputElement.value = '-5';
    inputElement.dispatchEvent(new Event('input'));
    
    fixture.detectChanges();
    await fixture.whenStable();
    
    expect(component.adjustment).toBe(-5);
  });
});
