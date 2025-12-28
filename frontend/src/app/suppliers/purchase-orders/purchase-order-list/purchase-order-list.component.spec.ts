import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PurchaseOrderListComponent } from './purchase-order-list.component';
import { SuppliersService } from '../../suppliers.service';
import { of } from 'rxjs';
import { RouterTestingModule } from '@angular/router/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { MatTableModule } from '@angular/material/table';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

describe('PurchaseOrderListComponent', () => {
  let component: PurchaseOrderListComponent;
  let fixture: ComponentFixture<PurchaseOrderListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [PurchaseOrderListComponent],
      imports: [
        HttpClientTestingModule,
        RouterTestingModule,
        MatTableModule,
        MatCardModule,
        MatButtonModule,
        MatIconModule
      ],
      providers: [SuppliersService]
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
