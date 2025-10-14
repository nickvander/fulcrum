import { Injectable } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ProductService } from './product';
import { CustomFieldService } from '../../settings/services/custom-field.service';
import { Product } from '../models/product.model';
import { CustomField } from '../../settings/models/custom-field.model';
import { combineLatest, Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

export interface ProductFormInitializationData {
  customFields: CustomField[];
  product?: Product;
  isEditMode: boolean;
  initialPrimaryImageId: number | null;
}

@Injectable({
  providedIn: 'root'
})
export class ProductFormInitializerService {

  constructor(
    private productService: ProductService,
    private customFieldService: CustomFieldService,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  initializeForm(isEditMode: boolean, productId: number | null): Observable<ProductFormInitializationData> {
    const navigation = this.router.getCurrentNavigation();
    const navigationState = navigation?.extras?.state;

    // Create observables for the data we need
    const customFields$ = this.customFieldService.getCustomFields().pipe(
      catchError(error => {
        console.error('Error getting custom fields:', error);
        return of([]); // Return empty array on error
      })
    );
    
    let product$ = of<Product | undefined>(undefined);
    if (isEditMode && productId) {
      product$ = this.productService.getProductById(productId).pipe(
        map(product => product as Product | undefined),
        catchError(error => {
          console.error('Error getting product by ID:', error);
          // Return undefined but don't error the entire operation
          return of(undefined);
        })
      );
    }

    // Combine the observables
    return combineLatest([customFields$, product$]).pipe(
      map(([customFields, product]) => {
        let initialPrimaryImageId: number | null = null;
        
        if (product && product.images) {
          const primaryImage = product.images.find(img => img.is_primary);
          if (primaryImage) {
            initialPrimaryImageId = primaryImage.id;
          }
        }

        return {
          customFields,
          product,
          isEditMode, // This is passed in from the component
          initialPrimaryImageId
        };
      })
    );
  }
}