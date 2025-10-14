import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { ProductFormInitializationData } from './product-form-initializer.service';

@Injectable()
export class ProductFormInitializerServiceMock {
  initializeForm(): Observable<ProductFormInitializationData> {
    // Return synchronous data for testing
    return of({
      customFields: [],
      product: undefined,
      isEditMode: false,
      initialPrimaryImageId: null
    });
  }
}