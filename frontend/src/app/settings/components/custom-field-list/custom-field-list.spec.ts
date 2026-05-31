import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { MatDialog } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { CustomFieldList } from './custom-field-list';
import { getTranslocoTestingModule } from '../../../testing/transloco-testing';

describe('CustomFieldList', () => {
  let component: CustomFieldList;
  let fixture: ComponentFixture<CustomFieldList>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CustomFieldList, HttpClientTestingModule, NoopAnimationsModule, getTranslocoTestingModule()],
      providers: [
        { provide: MatDialog, useValue: {} },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CustomFieldList);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
