import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ProductIngestion } from './product-ingestion';

describe('ProductIngestion', () => {
  let component: ProductIngestion;
  let fixture: ComponentFixture<ProductIngestion>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProductIngestion, HttpClientTestingModule]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ProductIngestion);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
