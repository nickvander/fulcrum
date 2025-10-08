import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ProductIngestion } from './product-ingestion';

describe('ProductIngestion', () => {
  let component: ProductIngestion;
  let fixture: ComponentFixture<ProductIngestion>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ProductIngestion]
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
