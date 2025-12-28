import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SupplierDetailComponent } from './supplier-detail.component';
import { ReactiveFormsModule } from '@angular/forms';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { MatInputModule } from '@angular/material/input';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { SuppliersService } from '../suppliers.service';

describe('SupplierDetailComponent', () => {
  let component: SupplierDetailComponent;
  let fixture: ComponentFixture<SupplierDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [SupplierDetailComponent],
      imports: [
        ReactiveFormsModule,
        HttpClientTestingModule,
        RouterTestingModule,
        MatInputModule,
        MatCardModule,
        MatButtonModule,
        NoopAnimationsModule
      ],
      providers: [SuppliersService]
    })
      .compileComponents();

    fixture = TestBed.createComponent(SupplierDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
