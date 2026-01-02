import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PurchaseOrderListComponent } from './purchase-order-list.component';
import { SuppliersService } from '../../suppliers.service';
import { DateRangeService } from '../../../shared/services/date-range.service';
import { of } from 'rxjs';
import { RouterTestingModule } from '@angular/router/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { MatTableModule } from '@angular/material/table';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSortModule } from '@angular/material/sort';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { CommonModule } from '@angular/common';
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { MatPaginatorModule } from '@angular/material/paginator';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { TranslocoTestingModule } from '@ngneat/transloco';

describe('PurchaseOrderListComponent', () => {
  let component: PurchaseOrderListComponent;
  let fixture: ComponentFixture<PurchaseOrderListComponent>;

  const suppliersServiceMock = {
    getSuppliers: () => of([]),
    getPurchaseOrders: () => of([])
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [],
      imports: [
        PurchaseOrderListComponent,
        CommonModule,
        MatTableModule,
        MatPaginatorModule,
        MatSortModule,
        MatIconModule,
        MatButtonModule,
        MatSelectModule,
        MatCardModule,
        MatFormFieldModule,
        MatInputModule,
        BrowserAnimationsModule,
        RouterTestingModule,
        HttpClientTestingModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, es: {} },
          translocoConfig: { availableLangs: ['en', 'es'], defaultLang: 'en' }
        })
      ],
      providers: [
        { provide: SuppliersService, useValue: suppliersServiceMock },
        DateRangeService
      ],
      schemas: [CUSTOM_ELEMENTS_SCHEMA]
    })
      .compileComponents();

    fixture = TestBed.createComponent(PurchaseOrderListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
