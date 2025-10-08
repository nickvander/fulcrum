import { TestBed } from '@angular/core/testing';
import { ProductList } from './product-list';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientTestingModule } from '@angular/common/http/testing';

describe('ProductList', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProductList, NoopAnimationsModule, HttpClientTestingModule],
    }).compileComponents();
  });

  it('should create the component', () => {
    const fixture = TestBed.createComponent(ProductList);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });
});
