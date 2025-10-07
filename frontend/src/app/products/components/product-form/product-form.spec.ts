import { TestBed } from '@angular/core/testing';
import { ProductForm } from './product-form';

describe('ProductForm', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ProductForm],
    }).compileComponents();
  });

  it('should create the component', () => {
    const fixture = TestBed.createComponent(ProductForm);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });
});
