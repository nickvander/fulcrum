import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule, JsonPipe } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatCardModule } from '@angular/material/card';
import { MatExpansionModule } from '@angular/material/expansion';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { ProductVariant } from '../../models/product.model';

@Component({
  selector: 'app-product-variants',
  standalone: true,
  imports: [
    CommonModule,
    JsonPipe,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatFormFieldModule,
    MatCardModule,
    MatExpansionModule,
    FormsModule,
    ReactiveFormsModule
  ],
  templateUrl: './product-variants.html',
  styleUrls: ['./product-variants.scss']
})
export class ProductVariantsComponent implements OnInit {
  @Input() productVariants: ProductVariant[] = [];
  @Output() variantsChanged = new EventEmitter<ProductVariant[]>();
  @Output() addVariant = new EventEmitter<void>();
  
  editableVariants: ProductVariant[] = [];
  isEditing: boolean = false;
  
  ngOnInit(): void {
    this.editableVariants = [...this.productVariants];
  }
  
  ngOnChanges(): void {
    this.editableVariants = [...this.productVariants];
  }
  
  onAddVariant(): void {
    const newVariant: ProductVariant = {
      id: 0, // Temporary ID, will be set by backend when saved
      product_id: 0, // Will be set when saving
      name: '',
      sku: '',
      price: 0,
      stock_quantity: 0,
      attributes: {}
    };
    this.editableVariants.push(newVariant);
    this.productVariants = [...this.editableVariants];
    this.addVariant.emit();
  }
  
  onEditVariant(index: number): void {
    this.isEditing = true;
  }
  
  onSaveVariants(): void {
    this.productVariants = [...this.editableVariants];
    this.variantsChanged.emit(this.productVariants);
    this.isEditing = false;
  }
  
  onCancelEdit(): void {
    this.editableVariants = [...this.productVariants];
    this.isEditing = false;
  }
  
  onRemoveVariant(index: number): void {
    this.editableVariants.splice(index, 1);
    this.productVariants = [...this.editableVariants];
    this.variantsChanged.emit(this.productVariants);
  }
  
  updateVariant(index: number, field: string, value: any): void {
    // Only update fields that exist on the ProductVariant interface
    const allowedFields = ['name', 'sku', 'price', 'stock_quantity', 'attributes'];
    if (allowedFields.includes(field)) {
      this.editableVariants[index] = { ...this.editableVariants[index], [field]: value };
    }
  }
  
  parseJsonSafely(value: string): Record<string, any> {
    if (!value) {
      return {};
    }
    try {
      return JSON.parse(value);
    } catch {
      // If parsing fails, return the current attributes value or an empty object
      return {};
    }
  }
}