import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { PurchasingComponent } from './purchasing.component';

describe('PurchasingComponent', () => {
  let component: PurchasingComponent;
  let fixture: ComponentFixture<PurchasingComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PurchasingComponent, RouterTestingModule],
    }).compileComponents();

    fixture = TestBed.createComponent(PurchasingComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
