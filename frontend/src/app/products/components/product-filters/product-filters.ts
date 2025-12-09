import { Component, Output, EventEmitter, OnInit } from '@angular/core';

import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormsModule } from '@angular/forms';
import { MatSliderModule } from '@angular/material/slider';
import { MatCheckboxModule } from '@angular/material/checkbox';

@Component({
  selector: 'app-product-filters',
  standalone: true,
  imports: [
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatFormFieldModule,
    FormsModule,
    MatSliderModule,
    MatCheckboxModule
],
  templateUrl: './product-filters.html',
  styleUrls: ['./product-filters.scss']
})
export class ProductFiltersComponent implements OnInit {
  @Output() filtersChanged = new EventEmitter<any>();
  @Output() filtersCleared = new EventEmitter<void>();

  // Filter properties
  category: string = '';
  brand: string = '';
  minPrice: number | null = null;
  maxPrice: number | null = null;
  minStock: number | null = null;
  maxStock: number | null = null;
  searchQuery: string = '';
  inStockOnly: boolean = false;

  categories: string[] = ['Electronics', 'Clothing', 'Home & Kitchen', 'Books', 'Toys', 'Sports']; // Example categories
  brands: string[] = ['Brand A', 'Brand B', 'Brand C', 'Generic']; // Example brands

  ngOnInit(): void {
    this.loadCategoriesAndBrands();
  }

  onFiltersChange(): void {
    const filters: any = {};
    
    if (this.category) filters.category = this.category;
    if (this.brand) filters.brand = this.brand;
    if (this.minPrice !== null) filters.min_price = this.minPrice;
    if (this.maxPrice !== null) filters.max_price = this.maxPrice;
    if (this.minStock !== null) filters.min_stock = this.minStock;
    if (this.maxStock !== null) filters.max_stock = this.maxStock;
    if (this.searchQuery) filters.search_term = this.searchQuery;
    if (this.inStockOnly) filters.in_stock_only = this.inStockOnly;

    this.filtersChanged.emit(filters);
  }

  onClearFilters(): void {
    this.category = '';
    this.brand = '';
    this.minPrice = null;
    this.maxPrice = null;
    this.minStock = null;
    this.maxStock = null;
    this.searchQuery = '';
    this.inStockOnly = false;
    
    this.filtersCleared.emit();
    this.onFiltersChange();
  }

  private loadCategoriesAndBrands(): void {
    // In a real implementation, you would fetch these from the backend
    // For now, using examples
    console.log('Loading categories and brands');
  }
}