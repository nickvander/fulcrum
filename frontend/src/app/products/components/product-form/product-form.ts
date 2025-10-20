import { Component, OnInit, OnDestroy, Input, Output, EventEmitter } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
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
import { ImageDialogComponent } from '../../../shared/components/image-dialog/image-dialog';
import { ConfirmationDialog } from '../../../shared/components/confirmation-dialog/confirmation-dialog';
import { ProductFormImageGalleryComponent } from './product-form-image-gallery.component';
import { ProductVariantsComponent } from '../product-variants/product-variants';
import { switchMap, map, takeUntil } from 'rxjs/operators';
import { forkJoin, of, Subject } from 'rxjs';
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
  ],
})
export class ProductForm implements OnInit {
  @Input() product?: Product | null;
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
    });
  }

  ngOnInit(): void {
    // Check if product is passed via @Input (side panel mode)
    if (this.product) {
      // Side panel mode - use the passed product
      this.isEditMode = true;
      this.productId = this.product.id || null;
      
      // Load the full product details to ensure all data (images, custom fields, etc.) is available
      this.productService.getProductById(this.product.id!).pipe(
        takeUntil(this.destroy$)
      ).subscribe({
        next: (fullProduct: Product) => {
          // Set the full product data
          this.product = fullProduct;
          this.productId = fullProduct.id || null;
          
          // Patch form values with the full product data
          if (fullProduct) {
            this.productForm.patchValue(fullProduct);
            
            // Store original values for dirty checking (only for edit mode)
            if (this.isEditMode) {
              this.originalValues = { ...fullProduct };
              
              // Store original custom field values
              this.originalCustomFieldValues = {};
              if (fullProduct.custom_fields) {
                fullProduct.custom_fields.forEach(fieldValue => {
                  this.originalCustomFieldValues[`custom_field_${fieldValue.custom_field_id}`] = fieldValue.value;
                });
              }
            }
          }
          
          // Load custom fields and handle initialization
          this.customFieldService.getCustomFields().pipe(
            takeUntil(this.destroy$)
          ).subscribe({
            next: (customFields: CustomField[]) => {
              this.customFields = customFields;
              this.addCustomFieldControls();
              this.patchCustomFieldValues();
            },
            error: (error: any) => {
              console.error('Error getting custom fields:', error);
              this.customFields = [];
              this.addCustomFieldControls();
            }
          });
          
          // Load product variants
          if (this.productId) {
            this.productService.getProductVariants(this.productId).pipe(
              takeUntil(this.destroy$)
            ).subscribe({
              next: (variants: ProductVariant[]) => {
                this.productVariants = variants;
              },
              error: (error: any) => {
                console.error('Error loading product variants:', error);
                this.productVariants = [];
              }
            });
          }
        },
        error: (error) => {
          console.error('Error loading full product details:', error);
          // Fallback to using the partial product data if full loading fails
          if (this.product) {
            this.productForm.patchValue(this.product);
            
            // Store original values for dirty checking (only for edit mode)
            if (this.isEditMode) {
              this.originalValues = { ...this.product };
              
              // Store original custom field values
              this.originalCustomFieldValues = {};
              if (this.product.custom_fields) {
                this.product.custom_fields.forEach(fieldValue => {
                  this.originalCustomFieldValues[`custom_field_${fieldValue.custom_field_id}`] = fieldValue.value;
                });
              }
            }
          }
          
          // Load custom fields anyway
          this.customFieldService.getCustomFields().pipe(
            takeUntil(this.destroy$)
          ).subscribe({
            next: (customFields: CustomField[]) => {
              this.customFields = customFields;
              this.addCustomFieldControls();
              this.patchCustomFieldValues();
            },
            error: (error: any) => {
              console.error('Error getting custom fields:', error);
              this.customFields = [];
              this.addCustomFieldControls();
            }
          });
        }
      });
    } else {
      // Route-based mode - use existing routing logic
      const idParam = this.route.snapshot.params['id'];
      const isEditMode = !!idParam;
      const productId = idParam ? +idParam : null;
      
      // Use the initialization service instead of complex observables in component
      this.productFormInitializer.initializeForm(isEditMode, productId).pipe(
        takeUntil(this.destroy$)
      ).subscribe({
        next: (initializationData: ProductFormInitializationData) => {
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
        }
      });
    }
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
    if (this.productForm.invalid || !this.isDirty) {
      return;
    }

    const formValue = this.productForm.value;
    const productData: any = {};
    const customFieldValues: { [key: string]: any } = {};

    Object.keys(formValue).forEach(key => {
      if (key.startsWith('custom_field_')) {
        customFieldValues[key.replace('custom_field_', '')] = formValue[key];
      } else {
        productData[key] = formValue[key];
      }
    });

    if (this.isEditMode && this.productId) {
      const updateObservables = [];
      const productId = this.productId;

      // 1. Update core product details if form is dirty
      if (this.productForm.dirty) {
        const productToUpdate: Product = { id: productId, ...productData };
        updateObservables.push(this.productService.updateProduct(productToUpdate));
        updateObservables.push(this.productService.saveCustomFieldValues(productId, customFieldValues));
      }

      // 2. Delete images marked for deletion
      if (this.imagesToDelete.length > 0) {
        this.imagesToDelete.forEach(imageId => {
          updateObservables.push(this.productService.deleteProductImage(productId, imageId));
        });
      }

      // 3. Set new primary image if it has changed
      const primaryImage = this.product?.images?.find(img => img.is_primary);
      const currentPrimaryId = primaryImage ? primaryImage.id : null;
      if (this.initialPrimaryImageId !== currentPrimaryId && currentPrimaryId) {
        updateObservables.push(this.productService.setPrimaryProductImage(productId, currentPrimaryId));
      }
      
      // 4. Upload new images (staged in edit mode, though current UI doesn't support it, this makes it robust)
      // This part of onFileSelected needs to be adjusted to stage images in edit mode too.
      // For now, this will handle any images that might get staged.
      if (this.stagedImages.length > 0) {
        this.stagedImages.forEach(file => {
          updateObservables.push(this.productService.uploadProductImage(productId, file));
        });
      }
      
      // 5. Handle product variants (create, update, delete)
      // For now, we'll just log these operations - in a real implementation, you'd implement the actual API calls
      console.log('Product variants to save:', this.productVariants);
      // TODO: Implement actual variant operations

      forkJoin(updateObservables.length > 0 ? updateObservables : [Promise.resolve()]).subscribe({
        next: () => {
          this.notificationService.showSuccess('Product updated successfully.');
          
          // Emit event instead of navigating if in side panel mode
          if (this.product) {
            this.productSaved.emit();
          } else {
            this.router.navigate(['/products']);
          }
        },
        error: (err) => this.notificationService.showError('Failed to update product.')
      });

    } else { // Create Mode
      this.productService.createProduct(productData).pipe(
        switchMap(newProduct => {
          const operations = [];
          // Save custom fields
          operations.push(this.productService.saveCustomFieldValues(newProduct.id, customFieldValues));
          
          // Upload staged images
          if (this.stagedImages.length > 0) {
            this.stagedImages.forEach(file => 
              operations.push(this.productService.uploadProductImage(newProduct.id, file))
            );
          }
          
          // Handle product variants
          // For now, we'll just log these operations - in a real implementation, you'd implement the actual API calls
          if (this.productVariants && this.productVariants.length > 0) {
            console.log('Creating variants for new product:', this.productVariants);
            // TODO: Implement actual variant creation operations after product is created
          }
          
          return forkJoin(operations.length > 0 ? operations : [Promise.resolve()]).pipe(map(() => newProduct));
        })
      ).subscribe({
        next: () => {
          this.notificationService.showSuccess('Product created successfully.');
          
          // Emit event instead of navigating if in side panel mode
          if (this.product) {
            this.productSaved.emit();
          } else {
            this.router.navigate(['/products']);
          }
        },
        error: (err) => this.notificationService.showError('Failed to create product.')
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

  onImageUpdated(event: {imageId: number, field: 'title' | 'description', value: string}): void {
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

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
