import { Injectable } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ProductService } from '../services/product';
import { CustomFieldService } from '../../settings/services/custom-field.service';
import { Product } from '../models/product.model';
import { CustomField } from '../../settings/models/custom-field.model';
import { Observable, of, combineLatest } from 'rxjs';
import { take, map, catchError, switchMap } from 'rxjs/operators';

export interface ProductFormData {
  isEditMode: boolean;
  product: Product | null;
  customFields: CustomField[];
}

@Injectable({
  providedIn: 'root'
})
export class ProductFormInitializerService {
  constructor(
    private customFieldService: CustomFieldService,
    private productService: ProductService,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  getInitializationData(): Observable<ProductFormData> {
    const idParam = this.route.snapshot.params['id'];
    const navigation = this.router.getCurrentNavigation();
    const navigationState = navigation?.extras?.state;

    // Get custom fields observable
    const customFields$ = this.customFieldService.getCustomFields().pipe(
      catchError(() => of([])) // Return empty array on error
    );

    if (idParam) {
      // Edit mode: get the specific product and custom fields
      return combineLatest([
        this.productService.getProductById(+idParam), // Get the specific product by ID
        customFields$
      ]).pipe(
        map(([product, customFields]) => {
          return {
            isEditMode: true,
            product: product || null,
            customFields
          };
        }),
        catchError(() => of({
          isEditMode: true,
          product: null,
          customFields: []
        }))
      );
    } else {
      // Create mode: just get custom fields
      return customFields$.pipe(
        map(customFields => {
          const result: ProductFormData = {
            isEditMode: false,
            product: null,
            customFields
          };

          // Pre-populate from navigation state if available
          if (navigationState && navigationState['productData']) {
            result.product = navigationState['productData'];
          }
          
          return result;
        }),
        catchError(() => of({
          isEditMode: false,
          product: null,
          customFields: []
        }))
      );
    }
  }
}