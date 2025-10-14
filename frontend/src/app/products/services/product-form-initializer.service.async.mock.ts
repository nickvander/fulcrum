import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';
import { ProductFormInitializationData } from './product-form-initializer.service';

@Injectable()
export class ProductFormInitializerServiceAsyncMock {

  initializeForm(isEditMode: boolean, productId: number | null): Observable<ProductFormInitializationData> {
    // Simulate a small delay to test async behavior, but keep it fast for tests
    return of({
      customFields: [],
      product: isEditMode ? {
        id: productId || 1,
        name: 'Test Product',
        sku: 'T001',
        description: '',
        default_resale_price: 100,
        cost_price: 50,
        manufacturer: 'Test Manufacturer',
        brand: 'Test Brand',
        category: 'Test Category',
        width: 10,
        height: 10,
        depth: 10,
        weight: 10,
        images: [
          { id: 1, product_id: 1, image_path: 'test.jpg', is_primary: 1, title: '', description: '' }
        ],
        custom_fields: []
      } as any : undefined,
      isEditMode,
      initialPrimaryImageId: isEditMode ? 1 : null
    }).pipe(delay(1)); // Small delay to maintain async behavior but keep tests fast
  }
}