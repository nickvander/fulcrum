import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PurchaseOrderEditComponent } from './purchase-order-edit.component';
import { SuppliersService } from '../../suppliers.service';
import { ReactiveFormsModule } from '@angular/forms';
import { RouterTestingModule } from '@angular/router/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('PurchaseOrderEditComponent', () => {
  let component: PurchaseOrderEditComponent;
  let fixture: ComponentFixture<PurchaseOrderEditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [PurchaseOrderEditComponent],
      imports: [
        ReactiveFormsModule,
        RouterTestingModule,
        HttpClientTestingModule,
        MatSelectModule,
        MatInputModule,
        MatCardModule,
        MatButtonModule,
        MatIconModule,
        NoopAnimationsModule
      ],
      providers: [SuppliersService]
    })
      .compileComponents();

    fixture = TestBed.createComponent(PurchaseOrderEditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
