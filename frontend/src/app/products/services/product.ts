import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap, switchMap, map } from 'rxjs';
import { Product, ProductImage } from '../models/product.model';
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

  getProducts(): Observable<Product[]> {
    return this.http.get<Product[]>(`${this.apiUrl}/`).pipe(
      map(products =>
        products.map(p => ({
          ...p,
          primary_image: p.images?.find(img => img.is_primary) ?? p.images?.[0],
        }))
      ),
      tap(products => {
        this._products.next(products);
      })
    );
  }

  searchProducts(query: string): Observable<Product[]> {
    return this.http.get<Product[]>(`${this.apiUrl}/search/?q=${query}`).pipe(
      tap(products => {
        this._products.next(products);
      })
    );
  }

  searchProductsBySku(sku: string): Observable<Product[]> {
    return this.http.get<Product[]>(`${this.apiUrl}/?sku=${sku}`);
  }

  createProduct(product: Omit<Product, 'id'>): Observable<Product> {
    return this.http.post<Product>(`${this.apiUrl}/`, product).pipe(
      tap(() => this.notificationService.showSuccess('Product created successfully!')),
      switchMap(newProduct =>
        this.getProducts().pipe(map(() => newProduct))
      )
    );
  }

  updateProduct(product: Product): Observable<Product> {
    return this.http.put<Product>(`${this.apiUrl}/${product.id}`, product).pipe(
      tap(() => this.notificationService.showSuccess('Product updated successfully!')),
      switchMap(updatedProduct =>
        this.getProducts().pipe(map(() => updatedProduct))
      )
    );
  }

  deleteProduct(id: number): Observable<unknown> {
    return this.http.delete(`${this.apiUrl}/${id}`).pipe(
      tap(() => this.notificationService.showSuccess('Product deleted successfully!')),
      switchMap(response =>
        this.getProducts().pipe(map(() => response))
      )
    );
  }

  uploadImage(file: File): Observable<{ file_path: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<{ file_path: string }>(`${environment.apiUrl}/uploads/`, formData);
  }

  identifyProductFromImage(filePath: string): Observable<Partial<Product>> {
    return this.http.post<Partial<Product>>(`${environment.apiUrl}/ai/identify-from-image`, {
      image_path: filePath,
    });
  }

  uploadProductImage(productId: number, file: File): Observable<ProductImage> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ProductImage>(`${this.apiUrl}/${productId}/images`, formData);
  }

  updateProductImage(productId: number, imageId: number, payload: { title?: string; description?: string }): Observable<any> {
    return this.http.put(`${this.apiUrl}/${productId}/images/${imageId}`, payload);
  }

  deleteProductImage(productId: number, imageId: number): Observable<unknown> {
    return this.http.delete(`${this.apiUrl}/${productId}/images/${imageId}`);
  }

  setPrimaryProductImage(productId: number, imageId: number): Observable<unknown> {
    return this.http.post(`${this.apiUrl}/${productId}/images/${imageId}/set-primary`, {});
  }

  adjustStock(productId: number, adjustment: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/${productId}/adjust-stock`, { adjustment }).pipe(
      tap(() => this.notificationService.showSuccess('Stock adjusted successfully!')),
      switchMap(() => this.getProducts())
    );
  }

  saveCustomFieldValues(productId: number, customFieldValues: { [key: string]: any }): Observable<any> {
    return this.http.post(`${this.apiUrl}/${productId}/custom-fields`, customFieldValues);
  }
}
