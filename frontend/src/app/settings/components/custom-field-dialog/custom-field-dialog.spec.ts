import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { CustomFieldDialog } from './custom-field-dialog';

describe('CustomFieldDialog', () => {
  let component: CustomFieldDialog;
  let fixture: ComponentFixture<CustomFieldDialog>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CustomFieldDialog, NoopAnimationsModule],
      providers: [
        { provide: MatDialogRef, useValue: {} },
        { provide: MAT_DIALOG_DATA, useValue: {} },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CustomFieldDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
