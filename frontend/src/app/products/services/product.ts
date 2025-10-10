import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { Product } from '../models/product.model';
import { NotificationService } from '../../core/services/notification.service';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ProductService {
  private apiUrl = `${environment.apiUrl}/products`;

  private readonly _products = new BehaviorSubject<Product[]>([]);
  readonly products$ = this._products.asObservable();

  constructor(
    private http: HttpClient,
    private notificationService: NotificationService
  ) {}

  getProducts(): void {
    this.http.get<Product[]>(this.apiUrl).subscribe(products => {
      this._products.next(products);
    });
  }

  searchProducts(query: string): void {
    this.http.get<Product[]>(`${this.apiUrl}/search/?q=${query}`).subscribe(products => {
      this._products.next(products);
    });
  }

  createProduct(product: Omit<Product, 'id'>): Observable<Product> {
    return this.http.post<Product>(this.apiUrl, product).pipe(
      tap(newProduct => {
        this._products.next([...this._products.value, newProduct]);
        this.notificationService.showSuccess('Product created successfully!');
      })
    );
  }

  updateProduct(product: Product): Observable<Product> {
    return this.http.put<Product>(`${this.apiUrl}/${product.id}`, product).pipe(
      tap(updatedProduct => {
        const products = this._products.value.map(p =>
          p.id === updatedProduct.id ? updatedProduct : p
        );
        this._products.next(products);
        this.notificationService.showSuccess('Product updated successfully!');
      })
    );
  }

  deleteProduct(id: number): Observable<unknown> {
    return this.http.delete(`${this.apiUrl}/${id}`).pipe(
      tap(() => {
        const products = this._products.value.filter(p => p.id !== id);
        this._products.next(products);
        this.notificationService.showSuccess('Product deleted successfully!');
      })
    );
  }

  uploadImage(file: File): Observable<{ file_path: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<{ file_path: string }>(`${environment.apiUrl}/uploads`, formData);
  }

  identifyProductFromImage(filePath: string): Observable<Partial<Product>> {
    return this.http.post<Partial<Product>>(`${environment.apiUrl}/ai/identify-from-image`, {
      image_path: filePath,
    });
  }

  uploadProductImage(productId: number, file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post(`${this.apiUrl}/${productId}/images`, formData);
  }

  deleteProductImage(productId: number, imageId: number): Observable<unknown> {
    return this.http.delete(`${this.apiUrl}/${productId}/images/${imageId}`);
  }

  setPrimaryProductImage(productId: number, imageId: number): Observable<unknown> {
    return this.http.post(`${this.apiUrl}/${productId}/images/${imageId}/set-primary`, {});
  }
}
