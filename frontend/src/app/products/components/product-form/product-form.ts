import { Component, OnInit, OnDestroy } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ProductService } from '../../services/product';
import { Product, ProductImage } from '../../models/product.model';
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
import { switchMap, map, takeUntil } from 'rxjs/operators';
import { forkJoin, of, Subject } from 'rxjs';
import { CustomField } from '../../../settings/models/custom-field.model';
import { NotificationService } from '../../../core/services/notification.service';
import { ProductFormInitializerService, ProductFormInitializationData } from '../../services/product-form-initializer.service';

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
  ],
})
export class ProductForm implements OnInit {
  productForm: FormGroup;
  isEditMode = false;
  product: Product | null = null;
  productId: number | null = null;
  customFields: CustomField[] = [];
  stagedImages: File[] = [];
  stagedImagePreviews: string[] = [];
  imagesToDelete: number[] = [];
  initialPrimaryImageId: number | null = null;
  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private productService: ProductService,
    private router: Router,
    private route: ActivatedRoute,
    private productFormInitializer: ProductFormInitializerService,
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
    // Determine edit mode from route params
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

  private handleInitializationData(data: ProductFormInitializationData): void {
    this.customFields = data.customFields;
    this.isEditMode = data.isEditMode;
    this.initialPrimaryImageId = data.initialPrimaryImageId;
    
    if (data.product) {
      this.product = data.product;
      this.productId = data.product.id || null;
      this.productForm.patchValue(data.product);
      this.patchCustomFieldValues();
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

    return (
      this.productForm.dirty ||
      this.stagedImages.length > 0 ||
      this.imagesToDelete.length > 0 ||
      (this.isEditMode && this.initialPrimaryImageId !== currentPrimaryId)
    );
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

      forkJoin(updateObservables.length > 0 ? updateObservables : [Promise.resolve()]).subscribe({
        next: () => {
          this.notificationService.showSuccess('Product updated successfully.');
          this.router.navigate(['/products']);
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
          
          return forkJoin(operations.length > 0 ? operations : [Promise.resolve()]).pipe(map(() => newProduct));
        })
      ).subscribe({
        next: () => {
          this.notificationService.showSuccess('Product created successfully.');
          this.router.navigate(['/products']);
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
          this.router.navigate(['/products']);
        }
      });
    } else {
      this.router.navigate(['/products']);
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

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
