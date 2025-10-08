import { TestBed } from '@angular/core/testing';
import { ProductForm } from './product-form';
import { RouterTestingModule } from '@angular/router/testing';

describe('ProductForm', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProductForm, RouterTestingModule],
    }).compileComponents();
  });

  it('should create the component', () => {
    const fixture = TestBed.createComponent(ProductForm);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });
});
