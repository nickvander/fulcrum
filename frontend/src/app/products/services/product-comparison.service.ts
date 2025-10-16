import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { Product } from '../models/product.model';

@Injectable({
  providedIn: 'root'
})
export class ProductComparisonService {
  private readonly _comparedProducts = new BehaviorSubject<Product[]>([]);
  readonly comparedProducts$ = this._comparedProducts.asObservable();

  constructor() {}

  addProduct(product: Product): void {
    const currentProducts = this._comparedProducts.value;
    // Don't add if already in comparison list
    if (!currentProducts.some(p => p.id === product.id)) {
      // Limit to max 4 products for comparison
      if (currentProducts.length < 4) {
        this._comparedProducts.next([...currentProducts, product]);
      }
    }
  }

  removeProduct(productId: number): void {
    const currentProducts = this._comparedProducts.value;
    const updatedProducts = currentProducts.filter(p => p.id !== productId);
    this._comparedProducts.next(updatedProducts);
  }

  clearAll(): void {
    this._comparedProducts.next([]);
  }

  getProducts(): Product[] {
    return this._comparedProducts.value;
  }

  isInComparison(productId: number): boolean {
    return this._comparedProducts.value.some(p => p.id === productId);
  }

  toggleProductInComparison(product: Product): void {
    if (this.isInComparison(product.id)) {
      this.removeProduct(product.id);
    } else {
      this.addProduct(product);
    }
  }
}