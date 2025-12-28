import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { BehaviorSubject, Observable, tap, switchMap, map, catchError, throwError } from 'rxjs';
import { Product, ProductImage, ProductVariant } from '../models/product.model';
import { PaginatedProducts } from '../models/paginated-products.model';
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
  ) { }

  getProducts(page: number = 1, pageSize: number = 10, filters?: any): Observable<PaginatedProducts> {
    let params = new HttpParams()
      .set('skip', (page - 1) * pageSize)
      .set('limit', pageSize);

    // Add any additional filters if provided
    if (filters) {
      Object.keys(filters).forEach(key => {
        if (filters[key] !== undefined && filters[key] !== null && filters[key] !== '') {
          params = params.set(key, filters[key]);
        }
      });
    }

    return this.http.get<PaginatedProducts>(this.apiUrl, { params }).pipe(
      map(response => {
        // If the response is an array (existing behavior), convert it to paginated format
        if (Array.isArray(response)) {
          const products = response.map((p: any) => ({
            ...p,
            primary_image: p.images?.find((img: any) => img.is_primary) ?? p.images?.[0],
          }));
          // For compatibility with existing single-page behavior
          return {
            data: products,
            currentPage: 1,
            totalPages: 1,
            totalItems: products.length,
            pageSize: products.length,
            hasNextPage: false,
            hasPrevPage: false
          };
        }
        // If it's already a paginated response, process it
        const paginatedProducts = response as any;
        if (paginatedProducts.data) {
          return {
            ...paginatedProducts,
            data: paginatedProducts.data.map((p: any) => ({
              ...p,
              primary_image: p.images?.find((img: any) => img.is_primary) ?? p.images?.[0],
            }))
          };
        }
        // Fallback to the original response structure
        return {
          data: paginatedProducts.map((p: any) => ({
            ...p,
            primary_image: p.images?.find((img: any) => img.is_primary) ?? p.images?.[0],
          })),
          currentPage: page,
          totalPages: Math.ceil(paginatedProducts.length / pageSize),
          totalItems: paginatedProducts.length,
          pageSize: pageSize,
          hasNextPage: page < Math.ceil(paginatedProducts.length / pageSize),
          hasPrevPage: page > 1
        };
      }),
      tap(response => {
        this._products.next(response.data);
      })
    );
  }

  // Legacy method for backward compatibility
  getProductsLegacy(): Observable<Product[]> {
    return this.http.get<Product[]>(this.apiUrl).pipe(
      map(products =>
        products.map((p: any) => ({
          ...p,
          primary_image: p.images?.find((img: any) => img.is_primary) ?? p.images?.[0],
        }))
      ),
      tap(products => {
        this._products.next(products);
      })
    );
  }

  getProductById(id: number): Observable<Product> {
    return this.http.get<Product>(`${this.apiUrl}/${id}`);
  }

  searchProducts(query: string, page: number = 1, pageSize: number = 10): Observable<PaginatedProducts> {
    return this.getProducts(page, pageSize, { q: query });
  }

  searchProductsBySku(sku: string, page: number = 1, pageSize: number = 10): Observable<PaginatedProducts> {
    let params = new HttpParams()
      .set('sku', sku)
      .set('skip', (page - 1) * pageSize)
      .set('limit', pageSize);

    return this.http.get<any>(this.apiUrl, { params }).pipe(
      map(response => this.transformToPaginated(response, page, pageSize))
    );
  }

  searchProductsAdvanced(filters: any, page: number = 1, pageSize: number = 10): Observable<PaginatedProducts> {
    return this.getProducts(page, pageSize, filters);
  }

  private transformToPaginatedAdvanced(response: any, page: number, pageSize: number): PaginatedProducts {
    // The response should already be in PaginatedProducts format
    if (response && response.data) {
      return {
        ...response,
        data: response.data.map((p: any) => ({
          ...p,
          primary_image: p.images?.find((img: any) => img.is_primary) ?? p.images?.[0],
        }))
      };
    }

    // Fallback if response is not in expected format
    const data = Array.isArray(response) ? response : (response.data || []);
    return {
      data: data.map((p: any) => ({
        ...p,
        primary_image: p.images?.find((img: any) => img.is_primary) ?? p.images?.[0],
      })),
      currentPage: page,
      totalPages: 1,
      totalItems: data.length,
      pageSize: pageSize,
      hasNextPage: false,
      hasPrevPage: false
    };
  }

  private transformToPaginated(response: any, page: number, pageSize: number): PaginatedProducts {
    // If the response is an array, convert it to paginated format
    if (Array.isArray(response)) {
      const products = response.map((p: any) => ({
        ...p,
        primary_image: p.images?.find((img: any) => img.is_primary) ?? p.images?.[0],
      }));

      return {
        data: products,
        currentPage: 1,
        totalPages: 1,
        totalItems: products.length,
        pageSize: products.length,
        hasNextPage: false,
        hasPrevPage: false
      };
    }

    // If it's already a paginated response, process it
    if (response.data) {
      return {
        ...response,
        data: response.data.map((p: any) => ({
          ...p,
          primary_image: p.images?.find((img: any) => img.is_primary) ?? p.images?.[0],
        }))
      };
    }

    // Fallback: treat response as array of products
    const products = Array.isArray(response) ? response : [];
    return {
      data: products.map((p: any) => ({
        ...p,
        primary_image: p.images?.find((img: any) => img.is_primary) ?? p.images?.[0],
      })),
      currentPage: page,
      totalPages: Math.ceil(products.length / pageSize),
      totalItems: products.length,
      pageSize: pageSize,
      hasNextPage: page < Math.ceil(products.length / pageSize),
      hasPrevPage: page > 1
    };
  }

  createProduct(product: Omit<Product, 'id'>): Observable<Product> {
    return this.http.post<Product>(`${this.apiUrl}/`, product).pipe(
      tap(() => this.notificationService.showSuccess('Product created successfully!')),
      switchMap(newProduct =>
        this.getProducts().pipe(
          tap(() => {
            // Update the local cache after refreshing
            const currentProducts = this._products.getValue();
            const productWithPrimaryImage = {
              ...newProduct,
              primary_image: newProduct.images?.find(img => img.is_primary) ?? newProduct.images?.[0]
            };
            // Find if the product already exists in the list
            const existingIndex = currentProducts.findIndex(p => p.id === newProduct.id);
            if (existingIndex >= 0) {
              // Update existing product
              const updatedProducts = [...currentProducts];
              updatedProducts[existingIndex] = productWithPrimaryImage;
              this._products.next(updatedProducts);
            } else {
              // Add new product
              this._products.next([...currentProducts, productWithPrimaryImage]);
            }
          }),
          map(() => newProduct)
        )
      )
    );
  }

  updateProduct(product: Product): Observable<Product> {
    return this.http.put<Product>(`${this.apiUrl}/${product.id}`, product).pipe(
      tap(() => this.notificationService.showSuccess('Product updated successfully!')),
      tap(updatedProduct => {
        // Update the local cache with the updated product
        const currentProducts = this._products.getValue();
        const updatedProducts = currentProducts.map(p =>
          p.id === updatedProduct.id ? { ...updatedProduct, primary_image: updatedProduct.images?.find(img => img.is_primary) ?? updatedProduct.images?.[0] } : p
        );
        this._products.next(updatedProducts);
      })
    );
  }

  deleteProduct(id: number): Observable<unknown> {
    return this.http.delete(`${this.apiUrl}/${id}`).pipe(
      tap(() => this.notificationService.showSuccess('Product deleted successfully!')),
      switchMap(response =>
        this.getProducts().pipe(map(() => response))
      ),
      catchError(error => {
        this.notificationService.showError('Error deleting product: ' + error.message);
        return throwError(() => error);
      })
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

  updateImageOrder(productId: number, imageIdsInOrder: number[]): Observable<any> {
    return this.http.put(`${this.apiUrl}/${productId}/images/order`, { image_ids: imageIdsInOrder }).pipe(
      tap(() => this.notificationService.showSuccess('Image order updated successfully!')),
      switchMap(() => this.getProducts())
    );
  }

  adjustStock(productId: number, adjustment: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/${productId}/adjust-stock`, { adjustment }).pipe(
      tap(() => this.notificationService.showSuccess('Stock adjusted successfully!')),
      switchMap(() => this.getProducts())
    );
  }

  adjustStockWithReason(productId: number, adjustment: number, reason?: string): Observable<any> {
    const body = {
      adjustment,
      reason: reason || null
    };
    return this.http.post(`${this.apiUrl}/${productId}/adjust-stock`, body).pipe(
      tap(() => this.notificationService.showSuccess('Stock adjusted successfully!')),
      switchMap(() => this.getProducts())
    );
  }

  saveCustomFieldValues(productId: number, customFieldValues: { [key: string]: any }): Observable<any> {
    return this.http.post(`${this.apiUrl}/${productId}/custom-fields`, customFieldValues);
  }

  deleteMultipleProducts(ids: number[]): Observable<any> {
    return this.http.delete(`${this.apiUrl}/`, {
      body: { ids }
    }).pipe(
      tap(() => this.notificationService.showSuccess('Selected products deleted successfully!'))
    );
  }

  getPurchaseHistory(productId: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/${productId}/purchase-history`);
  }

  // Product Variants API methods
  getProductVariants(productId: number): Observable<ProductVariant[]> {
    return this.http.get<ProductVariant[]>(`${this.apiUrl}/${productId}/variants`);
  }

  createProductVariant(productId: number, variant: Omit<ProductVariant, 'id'>): Observable<ProductVariant> {
    return this.http.post<ProductVariant>(`${this.apiUrl}/${productId}/variants`, variant).pipe(
      tap(() => this.notificationService.showSuccess('Product variant created successfully!')),
      tap((newVariant: ProductVariant) => {
        // Update the local cache to reflect the new variant
        const currentProducts = this._products.getValue();
        const updatedProducts = currentProducts.map(product => {
          if (product.id === productId) {
            // Add the new variant to this product
            const updatedProduct = { ...product } as Product & { variants?: ProductVariant[] };
            if (!updatedProduct.variants) {
              updatedProduct.variants = [];
            }
            updatedProduct.variants.push(newVariant);
            return updatedProduct;
          }
          return product;
        });
        this._products.next(updatedProducts);
      })
    );
  }

  updateProductVariant(productId: number, variantId: number, variant: Partial<ProductVariant>): Observable<ProductVariant> {
    return this.http.put<ProductVariant>(`${this.apiUrl}/${productId}/variants/${variantId}`, variant).pipe(
      tap(() => this.notificationService.showSuccess('Product variant updated successfully!')),
      tap((updatedVariant: ProductVariant) => {
        // Update the local cache to reflect the updated variant
        const currentProducts = this._products.getValue();
        const updatedProducts = currentProducts.map(product => {
          if (product.id === productId && (product as Product & { variants?: ProductVariant[] }).variants) {
            // Update the variant in this product
            const updatedProduct = { ...product } as Product & { variants?: ProductVariant[] };
            if (updatedProduct.variants) {
              updatedProduct.variants = updatedProduct.variants.map(v =>
                v.id === updatedVariant.id ? updatedVariant : v
              );
            }
            return updatedProduct;
          }
          return product;
        });
        this._products.next(updatedProducts);
      })
    );
  }

  deleteProductVariant(productId: number, variantId: number): Observable<ProductVariant> {
    return this.http.delete<ProductVariant>(`${this.apiUrl}/${productId}/variants/${variantId}`).pipe(
      tap(() => this.notificationService.showSuccess('Product variant deleted successfully!')),
      tap((deletedVariant: ProductVariant) => {
        // Update the local cache to reflect the deleted variant
        const currentProducts = this._products.getValue();
        const updatedProducts = currentProducts.map(product => {
          if (product.id === productId && (product as Product & { variants?: ProductVariant[] }).variants) {
            // Remove the deleted variant from this product
            const updatedProduct = { ...product } as Product & { variants?: ProductVariant[] };
            if (updatedProduct.variants) {
              updatedProduct.variants = updatedProduct.variants.filter(v => v.id !== deletedVariant.id);
            }
            return updatedProduct;
          }
          return product;
        });
        this._products.next(updatedProducts);
      })
    );
  }
}
