import { Component, OnInit, OnDestroy, Input, Output, EventEmitter } from '@angular/core';
import { FormsModule, FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ProductService } from '../../services/product';
import { Product, ProductImage } from '../../models/product.model';
import { ProductVariant } from '../../models/product.model';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatDialog } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTabsModule } from '@angular/material/tabs';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { ImageDialogComponent } from '../../../shared/components/image-dialog/image-dialog';
import { ConfirmationDialog } from '../../../shared/components/confirmation-dialog/confirmation-dialog';
import { ProductFormImageGalleryComponent } from './product-form-image-gallery.component';
import { ProductVariantsComponent } from '../product-variants/product-variants';
import { switchMap, map, takeUntil, catchError, tap } from 'rxjs/operators';
import { forkJoin, of, Subject, Observable } from 'rxjs';
import { CustomField } from '../../../settings/models/custom-field.model';
import { NotificationService } from '../../../core/services/notification.service';
import { ProductFormInitializerService, ProductFormInitializationData } from '../../services/product-form-initializer.service';
import { CustomFieldService } from '../../../settings/services/custom-field.service';

@Component({
  selector: 'app-product-form',
  templateUrl: './product-form.html',
  styleUrl: './product-form.scss',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatListModule,
    MatTooltipModule,
    ProductFormImageGalleryComponent,
    ProductVariantsComponent,
    MatTabsModule,
    MatSlideToggleModule,
    MatAutocompleteModule
  ],
})
export class ProductForm implements OnInit {
  @Input() product?: Product | null;
  @Input() isDialogMode: boolean = false;
  @Output() productSaved = new EventEmitter<void>();
  @Output() formClosed = new EventEmitter<void>();

  productForm: FormGroup;
  isEditMode = false;
  productId: number | null = null;
  customFields: CustomField[] = [];
  stagedImages: File[] = [];
  stagedImagePreviews: string[] = [];
  imagesToDelete: number[] = [];
  initialPrimaryImageId: number | null = null;
  originalValues: any = {};
  originalCustomFieldValues: any = {};
  productVariants: ProductVariant[] = [];
  bundleComponents: any[] = [];
  availableProducts: Product[] = [];
  returnToPO = false;
  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private productService: ProductService,
    private router: Router,
    private route: ActivatedRoute,
    private productFormInitializer: ProductFormInitializerService,
    private customFieldService: CustomFieldService,
    private notificationService: NotificationService,
    private dialog: MatDialog
  ) {
    this.productForm = this.fb.group({
      name: ['', Validators.required],
      sku: ['', Validators.required],
      description: [''],
      default_resale_price: [0, [Validators.required, Validators.min(0)]],
      cost_price: [0, [Validators.min(0)]],
      manufacturer: [''],
      brand: [''],
      category: [''],
      width: [0, [Validators.min(0)]],
      height: [0, [Validators.min(0)]],
      depth: [0, [Validators.min(0)]],
      weight: [0, [Validators.min(0)]],
      is_bundle: [false],
    });
  }

  ngOnInit(): void {
    console.log('ProductForm: ngOnInit started');

    // Check if we're coming from creating a product for a PO
    this.route.queryParams.pipe(takeUntil(this.destroy$)).subscribe(params => {
      if (params['returnTo'] === 'po') {
        this.returnToPO = true;
      }
    });

    // Check if product is passed via @Input (side panel mode)
    if (this.product) {
      console.log('ProductForm: Side panel mode');
      this.initializeSidePanelMode();
    } else {
      console.log('ProductForm: Route mode');
      this.initializeRouteMode();
    }
  }

  returnToPurchaseOrder(): void {
    // Navigate back to PO creation with saved state
    this.router.navigate(['/suppliers/po/create']);
  }

  private initializeSidePanelMode(): void {
    console.log('ProductForm: initializeSidePanelMode');
    this.isEditMode = !!this.product!.id;
    this.productId = this.product!.id || null;

    // If we have an ID, load full details. If not (e.g. creating a bundle from existing), allow using passed product as is.
    const product$ = this.productId
      ? this.productService.getProductById(this.productId).pipe(
        catchError(error => {
          console.error('Error loading full product details:', error);
          return of(this.product!); // Fallback to partial product
        })
      )
      : of(this.product!);

    const customFields$ = this.customFieldService.getCustomFields().pipe(
      catchError(error => {
        console.error('Error getting custom fields:', error);
        return of([] as CustomField[]);
      })
    );

    const variants$ = this.productId
      ? this.productService.getProductVariants(this.productId).pipe(
        catchError(error => {
          console.error('Error loading product variants:', error);
          return of([] as ProductVariant[]);
        })
      )
      : of([] as ProductVariant[]);

    forkJoin({
      product: product$,
      customFields: customFields$,
      variants: variants$
    }).pipe(
      takeUntil(this.destroy$)
    ).subscribe({
      next: ({ product, customFields, variants }) => {
        console.log('ProductForm: Side panel data loaded');
        // Handle Product Data
        this.product = product;
        this.productId = product.id || null;

        if (product) {
          this.productForm.patchValue(product);

          if (this.isEditMode) {
            this.originalValues = { ...product };
            this.originalCustomFieldValues = {};
            if (product.custom_fields) {
              product.custom_fields.forEach(fieldValue => {
                this.originalCustomFieldValues[`custom_field_${fieldValue.custom_field_id}`] = fieldValue.value;
              });
            }
          }

          // Handle Bundles - Logic copied from handleInitializationData
          if (product.bundle_components) {
            this.bundleComponents = product.bundle_components.map(bc => {
              // If coming from backend, it might have nested component.
              // If coming from onCreateParentBundle, it matches the structure directly but 'component' inner obj might be missing or different.
              const component = (bc as any).component;
              let stock = 0;
              if (component && component.inventory_items) {
                stock = component.inventory_items.reduce((acc: any, item: any) => acc + item.quantity, 0);
              } else if ((bc as any).component_stock !== undefined) {
                // Fallback if stock is pre-calculated or passed
                stock = (bc as any).component_stock;
              }

              return {
                ...bc,
                component_name: component?.name || bc.component_name || 'Loading...',
                component_image: component?.primary_image?.image_path || bc.component_image,
                component_stock: stock,
                component_cost: component?.cost_price || (bc as any).component_cost || 0
              };
            });

            // If creating a bundle, update the cost if needed
            if (!this.isEditMode && product.is_bundle) {
              this.updateSuggestedBundleCost();
            }
          }
        }

        // Handle Custom Fields
        this.customFields = customFields;
        this.addCustomFieldControls();
        this.patchCustomFieldValues();

        // Handle Variants
        this.productVariants = variants;
      },
      error: (err) => console.error('Error initializing side panel', err)
    });
  }

  private initializeRouteMode(): void {
    console.log('ProductForm: initializeRouteMode');
    // Route-based mode - use existing routing logic
    const idParam = this.route.snapshot.params['id'];
    const isEditMode = !!idParam;
    const productId = idParam ? +idParam : null;

    console.log('ProductForm: calling initializeForm');
    // Use the initialization service instead of complex observables in component
    this.productFormInitializer.initializeForm(isEditMode, productId).pipe(
      takeUntil(this.destroy$)
    ).subscribe({
      next: (initializationData: ProductFormInitializationData) => {
        console.log('ProductForm: initializeForm next');
        this.handleInitializationData(initializationData);
      },
      error: (error) => {
        console.error('Error initializing form:', error);
        // Fallback to safe defaults
        this.handleInitializationData({
          customFields: [],
          isEditMode,
          initialPrimaryImageId: null
        });
      },
      complete: () => {
        console.log('ProductForm: initializeForm complete');
      }
    });
  }

  private handleInitializationData(data: ProductFormInitializationData): void {
    this.customFields = data.customFields;
    this.isEditMode = data.isEditMode;
    this.initialPrimaryImageId = data.initialPrimaryImageId;

    if (data.product) {
      this.product = data.product;
      this.productId = data.product.id || null;
      this.productForm.patchValue(data.product);

      // Store original values for dirty checking (only for edit mode)
      if (this.isEditMode) {
        this.originalValues = { ...data.product };
        this.patchCustomFieldValues();

        // Store original custom field values
        this.originalCustomFieldValues = {};
        if (data.product.custom_fields) {
          data.product.custom_fields.forEach(fieldValue => {
            this.originalCustomFieldValues[`custom_field_${fieldValue.custom_field_id}`] = fieldValue.value;
          });
        }
      }

      // Handle Bundles
      if (data.product.bundle_components) {
        this.bundleComponents = data.product.bundle_components.map(bc => {
          const component = (bc as any).component;
          let stock = 0;
          if (component && component.inventory_items) {
            stock = component.inventory_items.reduce((acc: any, item: any) => acc + item.quantity, 0);
          }
          return {
            ...bc,
            component_name: component?.name || bc.component_name || 'Loading...',
            component_image: component?.primary_image?.image_path || bc.component_image,
            component_stock: stock,
            component_cost: component?.cost_price || 0
          };
        });
      }
    }

    // Handle navigation state for pre-filled data
    const navigation = this.router.getCurrentNavigation();
    const navigationState = navigation?.extras?.state;
    if (navigationState && navigationState['productData']) {
      const productData = navigationState['productData'];
      const patchData: { [key: string]: any } = {};

      Object.keys(this.productForm.controls).forEach(key => {
        if (productData.hasOwnProperty(key)) {
          patchData[key] = productData[key];
        }
      });

      this.productForm.patchValue(patchData);
    }

    // Add custom field controls after getting the data
    this.addCustomFieldControls();
  }

  addCustomFieldControls(): void {
    this.customFields.forEach(field => {
      this.productForm.addControl(`custom_field_${field.id}`, this.fb.control(''));
    });
  }

  patchCustomFieldValues(): void {
    if (this.product && this.product.custom_fields) {
      this.product.custom_fields.forEach(fieldValue => {
        const control = this.productForm.get(`custom_field_${fieldValue.custom_field_id}`);
        if (control) {
          control.patchValue(fieldValue.value);
        }
      });
    }
  }

  get isDirty(): boolean {
    const primaryImage = this.product?.images?.find(img => img.is_primary);
    const currentPrimaryId = primaryImage ? primaryImage.id : null;

    // Check if there are actual changes to form controls by comparing to original values
    let formControlsChanged = false;

    if (this.isEditMode) {
      // Compare current form values with original values for standard fields
      const standardFields = [
        'name', 'sku', 'description', 'default_resale_price', 'cost_price',
        'manufacturer', 'brand', 'category', 'width', 'height', 'depth', 'weight'
      ];

      for (const key of standardFields) {
        const control = this.productForm.get(key);
        if (control) {
          // Convert values to the same type for comparison to avoid type mismatches
          const controlValue = control.value;
          const originalValue = this.originalValues[key];

          // Handle potential type differences (e.g., number vs string)
          if (String(controlValue) !== String(originalValue)) {
            formControlsChanged = true;
            break;
          }
        }
      }

      // Also check custom field values
      if (!formControlsChanged) {
        for (const key of Object.keys(this.productForm.controls)) {
          if (key.startsWith('custom_field_')) {
            const control = this.productForm.get(key);
            if (control) {
              const originalValue = this.originalCustomFieldValues[key];
              if (String(control.value) !== String(originalValue)) {
                formControlsChanged = true;
                break;
              }
            }
          }
        }
      }
    } else {
      // For create mode, check if any field has any value (indicating user input)
      for (const key of Object.keys(this.productForm.controls)) {
        const control = this.productForm.get(key);
        if (control && control.value && control.value !== '' && control.value !== null && control.value !== undefined) {
          formControlsChanged = true;
          break;
        }
      }
    }

    // Check if there are actual image changes (not just loading the form)
    const imageChanges = (
      this.stagedImages.length > 0 ||
      this.imagesToDelete.length > 0 ||
      (this.isEditMode && this.initialPrimaryImageId !== null && this.initialPrimaryImageId !== currentPrimaryId)
    );

    return formControlsChanged || imageChanges;
  }

  getImageUrl(imagePath: string): string {
    // Backend serves images from the 'uploads/product_images' directory.
    return `/uploads/product_images/${imagePath}`;
  }

  onSubmit(): void {
    if (this.productForm.invalid) {
      return;
    }

    const formValue = this.productForm.value;
    const productData: Partial<Product> = {
      name: formValue.name,
      sku: formValue.sku,
      description: formValue.description,
      default_resale_price: formValue.default_resale_price,
      cost_price: formValue.cost_price,
      manufacturer: formValue.manufacturer,
      brand: formValue.brand,
      category: formValue.category,
      width: formValue.width,
      height: formValue.height,
      depth: formValue.depth,
      weight: formValue.weight,
      is_bundle: formValue.is_bundle,
      bundle_components: formValue.is_bundle ? this.bundleComponents.map(bc => ({
        component_id: bc.component_id,
        quantity: bc.quantity
      })) : []
    };

    // Handle custom fields
    const customFieldValues: { [key: number]: any } = {};
    this.customFields.forEach(field => {
      const controlName = `custom_field_${field.id}`;
      if (formValue[controlName] !== undefined) {
        customFieldValues[field.id] = formValue[controlName];
      }
    });

    if (this.isEditMode && this.productId) {
      this.productService.updateProduct({ ...productData, id: this.productId } as Product).pipe(
        switchMap(updatedProduct => {
          // Save custom fields
          if (Object.keys(customFieldValues).length > 0) {
            return this.productService.saveCustomFieldValues(updatedProduct.id, customFieldValues).pipe(
              map(() => updatedProduct)
            );
          }
          return of(updatedProduct);
        }),
        switchMap(updatedProduct => {
          // Handle image deletions
          if (this.imagesToDelete.length > 0) {
            const deleteObservables = this.imagesToDelete.map(imageId =>
              this.productService.deleteProductImage(updatedProduct.id, imageId)
            );
            return forkJoin(deleteObservables).pipe(map(() => updatedProduct));
          }
          return of(updatedProduct);
        }),
        switchMap(updatedProduct => {
          // Handle new image uploads
          if (this.stagedImages.length > 0) {
            const uploadObservables = this.stagedImages.map(image =>
              this.productService.uploadProductImage(updatedProduct.id, image)
            );
            return forkJoin(uploadObservables).pipe(map(() => updatedProduct));
          }
          return of(updatedProduct);
        }),
        switchMap(updatedProduct => {
          // Handle primary image update
          const primaryImage = this.product?.images?.find(img => img.is_primary);
          if (primaryImage && primaryImage.id !== this.initialPrimaryImageId) {
            return this.productService.setPrimaryProductImage(updatedProduct.id, primaryImage.id).pipe(
              map(() => updatedProduct)
            );
          }
          return of(updatedProduct);
        })
      ).subscribe({
        next: () => {
          this.notificationService.showSuccess('Product updated successfully');
          // Emit event instead of navigating if in side panel mode
          if (this.product) {
            this.productSaved.emit();
          } else {
            this.router.navigate(['/products']);
          }
        },
        error: (error) => {
          console.error('Error updating product:', error);
          this.notificationService.showError('Error updating product');
        }
      });

    } else {
      this.productService.createProduct(productData as Product).pipe(
        switchMap(newProduct => {
          // Save custom fields
          if (Object.keys(customFieldValues).length > 0) {
            return this.productService.saveCustomFieldValues(newProduct.id, customFieldValues).pipe(
              map(() => newProduct)
            );
          }
          return of(newProduct);
        }),
        switchMap(newProduct => {
          // Handle image uploads
          if (this.stagedImages.length > 0) {
            const uploadObservables = this.stagedImages.map(image =>
              this.productService.uploadProductImage(newProduct.id, image)
            );
            return forkJoin(uploadObservables).pipe(map(() => newProduct));
          }
          return of(newProduct);
        })
      ).subscribe({
        next: () => {
          this.notificationService.showSuccess('Product created successfully');
          // Emit event instead of navigating if in side panel mode
          if (this.product) {
            this.productSaved.emit();
          } else {
            this.router.navigate(['/products']);
          }
        },
        error: (error) => {
          console.error('Error creating product:', error);
          this.notificationService.showError('Error creating product');
        }
      });
    }
  }

  onCancel(): void {
    if (this.isDirty) {
      const dialogRef = this.dialog.open(ConfirmationDialog, {
        data: {
          title: 'Discard changes?',
          message: 'You have unsaved changes. Are you sure you want to discard them?'
        }
      });
      dialogRef.afterClosed().subscribe(result => {
        if (result) {
          // Emit event instead of navigating if in side panel mode
          if (this.product) {
            this.formClosed.emit();
          } else {
            this.router.navigate(['/products']);
          }
        }
      });
    } else {
      // Emit event instead of navigating if in side panel mode
      if (this.product) {
        this.formClosed.emit();
      } else {
        this.router.navigate(['/products']);
      }
    }
  }

  // Methods to handle events from the child component
  onStagedImagesChange(images: File[]): void {
    this.stagedImages = images;
  }

  onStagedImagePreviewsChange(previews: string[]): void {
    this.stagedImagePreviews = previews;
  }

  onImagesToDelete(imageIds: number[]): void {
    this.imagesToDelete = [...this.imagesToDelete, ...imageIds];
    // Also remove from the product images if we have it
    if (this.product && this.product.images) {
      imageIds.forEach(id => {
        const index = this.product!.images!.findIndex(img => img.id === id);
        if (index > -1) {
          this.product!.images!.splice(index, 1);
        }
      });
    }
  }

  onPrimaryImageChange(imageId: number | null): void {
    if (imageId === null) {
      return; // Handle null case gracefully
    }
    if (this.product && this.product.images) {
      this.product.images.forEach(img => {
        img.is_primary = img.id === imageId ? 1 : 0;
      });
    }
  }

  onImageUpdated(event: { imageId: number, field: 'title' | 'description', value: string }): void {
    if (this.product && this.product.images) {
      const image = this.product.images.find(img => img.id === event.imageId);
      if (image) {
        image[event.field] = event.value;
      }
    }
  }

  onAddVariant(): void {
    // Create a new variant object with default values using the correct structure
    const newVariant: ProductVariant = {
      id: 0, // Temporary ID, will be set by backend when saved
      product_id: this.productId || 0,
      name: 'New Variant',
      sku: '',
      price: 0,
      stock_quantity: 0,
      attributes: {}
    };

    // Add the new variant to the list
    this.productVariants = [...this.productVariants, newVariant];
  }

  onExistingImagesOrderChange(orderedImages: ProductImage[]): void {
    if (this.product) {
      this.product.images = orderedImages;
      // Save the new order to the backend if the product already exists
      if (this.product.id) {
        const orderedImageIds = orderedImages.map(img => img.id!);
        this.productService.updateImageOrder(this.product.id, orderedImageIds).subscribe({
          next: () => {
            console.log('Image order updated successfully');
          },
          error: (error) => {
            console.error('Error updating image order:', error);
            this.notificationService.showError('Error updating image order');
            // Revert to the previous order
            // (In a real implementation, you might want to handle this differently)
          }
        });
      }
    }
  }

  onImageError(event: any): void {
    event.target.src = 'assets/placeholder.jpg';
  }

  onAddBundleComponent(product: Product): void {
    const existing = this.bundleComponents.find(c => c.component_id === product.id);
    if (existing) {
      existing.quantity++;
    } else {
      let stock = 0;
      if (product.inventory_items) {
        stock = product.inventory_items.reduce((acc, item) => acc + item.quantity, 0);
      }

      this.bundleComponents.push({
        component_id: product.id,
        component_name: product.name,
        component_image: product.primary_image?.image_path || (product.images && product.images.length > 0 ? product.images[0].image_path : undefined),
        quantity: 1,
        component_stock: stock,
        component_cost: product.cost_price || 0
      });
    }
    this.updateSuggestedBundleCost();
  }

  onRemoveBundleComponent(index: number): void {
    this.bundleComponents.splice(index, 1);
    this.updateSuggestedBundleCost();
  }

  updateSuggestedBundleCost(): void {
    if (this.productForm.get('is_bundle')?.value) {
      const totalCost = this.bundleComponents.reduce((acc, c) => acc + ((c.component_cost || 0) * c.quantity), 0);
      this.productForm.patchValue({ cost_price: totalCost });
    }
  }

  searchProducts(query: string): void {
    if (query.length < 2) return;
    this.productService.searchProductsIsolated(query).subscribe(res => {
      this.availableProducts = res.data.filter(p => p.id !== this.productId);
    });
  }

  getMarketplaceName(id: number): string {
    switch (id) {
      case 1: return 'Amazon';
      case 2: return 'eBay';
      case 3: return 'Shopify';
      case 4: return 'MercadoLibre';
      default: return 'Marketplace ' + id;
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
