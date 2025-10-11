import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { StockAdjustmentDialog } from './stock-adjustment-dialog';

describe('StockAdjustmentDialog', () => {
  let component: StockAdjustmentDialog;
  let fixture: ComponentFixture<StockAdjustmentDialog>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StockAdjustmentDialog, NoopAnimationsModule],
      providers: [
        { provide: MatDialogRef, useValue: {} },
        { provide: MAT_DIALOG_DATA, useValue: {} },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(StockAdjustmentDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
