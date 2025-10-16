import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Product } from '../../models/product.model';

@Component({
  selector: 'app-product-comparison',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatTableModule,
    MatTooltipModule
  ],
  templateUrl: './product-comparison.html',
  styleUrls: ['./product-comparison.scss']
})
export class ProductComparisonComponent implements OnInit {
  @Input() products: Product[] = [];
  @Output() closeComparison = new EventEmitter<void>();
  @Output() exportComparison = new EventEmitter<Product[]>();

  displayedColumns: string[] = ['attribute'];
  comparisonData: any[] = [];
  maxProductsForComparison = 4; // Maximum number of products to compare

  ngOnInit(): void {
    this.updateComparisonData();
  }

  ngOnChanges(): void {
    this.updateComparisonData();
  }

  updateComparisonData(): void {
    if (this.products.length === 0) return;

    // Set up column headers for each product
    this.displayedColumns = ['attribute', ...this.products.map((_, index) => `product${index}`)];

    // Define the attributes to compare
    const attributes = [
      { key: 'name', label: 'Name', type: 'text' },
      { key: 'sku', label: 'SKU', type: 'text' },
      { key: 'description', label: 'Description', type: 'text' },
      { key: 'default_resale_price', label: 'Price', type: 'currency' },
      { key: 'cost_price', label: 'Cost Price', type: 'currency' },
      { key: 'manufacturer', label: 'Manufacturer', type: 'text' },
      { key: 'brand', label: 'Brand', type: 'text' },
      { key: 'category', label: 'Category', type: 'text' },
      { key: 'width', label: 'Width', type: 'number' },
      { key: 'height', label: 'Height', type: 'number' },
      { key: 'depth', label: 'Depth', type: 'number' },
      { key: 'weight', label: 'Weight', type: 'number' },
    ];

    // Create comparison data rows
    this.comparisonData = attributes.map(attr => {
      const row: any = { attribute: attr.label };
      this.products.forEach((product, index) => {
        const value = (product as any)[attr.key];
        row[`product${index}`] = this.formatValue(value, attr.type);
      });
      return row;
    });
  }

  formatValue(value: any, type: string): string {
    if (value === null || value === undefined) {
      return 'N/A';
    }
    
    switch (type) {
      case 'currency':
        return typeof value === 'number' ? `$${value.toFixed(2)}` : value;
      case 'number':
        return typeof value === 'number' ? value.toString() : value;
      default:
        return value.toString();
    }
  }

  onExportComparison(): void {
    this.exportComparison.emit(this.products);
  }

  onClose(): void {
    this.closeComparison.emit();
  }

  removeProduct(index: number): void {
    this.products.splice(index, 1);
    this.updateComparisonData();
  }

  getImageUrl(imagePath: string): string {
    // Backend serves images from the 'uploads/product_images' directory.
    return `/uploads/product_images/${imagePath}`;
  }

  onImageError(event: any): void {
    // Set a placeholder image if the image fails to load
    event.target.src = '/uploads/product_images/placeholder.jpg';
  }

  trackByFn(index: number, item: any): any {
    return index;
  }

  hasDifference(element: any, productIndex: number): boolean {
    // Check if this product's value is different from others in the same attribute row
    if (this.products.length <= 1) return false;
    
    const currentProductValue = element[`product${productIndex}`];
    
    // Compare with other products in the same row
    for (let i = 0; i < this.products.length; i++) {
      if (i !== productIndex) {
        const otherProductValue = element[`product${i}`];
        if (currentProductValue !== otherProductValue) {
          return true;
        }
      }
    }
    
    return false;
  }
}