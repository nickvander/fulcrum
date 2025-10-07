import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { Product } from '../models/product.model';

const MOCK_PRODUCTS: Product[] = [
  { id: 1, name: 'Laptop Pro', sku: 'LP-001', description: 'High-end laptop', default_resale_price: 1499.99 },
  { id: 2, name: 'Wireless Mouse', sku: 'WM-002', description: 'Ergonomic wireless mouse', default_resale_price: 29.99 },
  { id: 3, name: 'Mechanical Keyboard', sku: 'MK-003', description: 'RGB mechanical keyboard', default_resale_price: 129.99 },
  { id: 4, name: '4K Monitor', sku: '4KM-004', description: '27-inch 4K UHD monitor', default_resale_price: 399.99 },
  { id: 5, name: 'USB-C Hub', sku: 'UCH-005', description: '7-in-1 USB-C hub', default_resale_price: 49.99 },
];

@Injectable({
  providedIn: 'root'
})
export class ProductService {
  private apiUrl = '/api/v1/products'; // TODO: Use environment variable

  constructor(private http: HttpClient) {}

  getProducts(): Observable<Product[]> {
    // TODO: Replace with actual API call
    return of(MOCK_PRODUCTS);
  }
}
