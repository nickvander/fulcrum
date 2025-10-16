import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { FormsModule } from '@angular/forms';
import { MatSliderModule } from '@angular/material/slider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ProductFiltersComponent } from './product-filters';

describe('ProductFiltersComponent', () => {
  let component: ProductFiltersComponent;
  let fixture: ComponentFixture<ProductFiltersComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        MatIconModule,
        MatButtonModule,
        MatInputModule,
        MatSelectModule,
        MatFormFieldModule,
        MatCheckboxModule,
        MatSliderModule,
        MatTooltipModule,
        FormsModule,
        ProductFiltersComponent
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ProductFiltersComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should emit filtersChanged event when filter properties change', () => {
    spyOn(component.filtersChanged, 'emit');

    component.category = 'Electronics';
    component.onFiltersChange();

    expect(component.filtersChanged.emit).toHaveBeenCalledWith({ category: 'Electronics' });
  });

  it('should emit filtersChanged event when multiple filters are applied', () => {
    spyOn(component.filtersChanged, 'emit');

    component.category = 'Electronics';
    component.brand = 'Brand A';
    component.minPrice = 10;
    component.maxPrice = 100;
    component.onFiltersChange();

    expect(component.filtersChanged.emit).toHaveBeenCalledWith({
      category: 'Electronics',
      brand: 'Brand A',
      min_price: 10,
      max_price: 100
    });
  });

  it('should emit filtersCleared event when filters are cleared', () => {
    spyOn(component.filtersCleared, 'emit');
    spyOn(component.filtersChanged, 'emit');

    component.onClearFilters();

    expect(component.filtersCleared.emit).toHaveBeenCalled();
    expect(component.filtersChanged.emit).toHaveBeenCalledWith({});
  });

  it('should have default filter values', () => {
    expect(component.category).toBe('');
    expect(component.brand).toBe('');
    expect(component.minPrice).toBeNull();
    expect(component.maxPrice).toBeNull();
    expect(component.minStock).toBeNull();
    expect(component.maxStock).toBeNull();
    expect(component.searchQuery).toBe('');
    expect(component.inStockOnly).toBeFalse();
  });

  it('should update filters when search query changes', () => {
    spyOn(component.filtersChanged, 'emit');
    
    component.searchQuery = 'test product';
    component.onFiltersChange();
    
    expect(component.filtersChanged.emit).toHaveBeenCalledWith({ search_term: 'test product' });
  });
});