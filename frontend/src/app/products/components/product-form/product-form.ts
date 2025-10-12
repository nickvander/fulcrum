import { Component, OnInit } from '@angular/core';
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
import { ImageDialogComponent } from '../../../shared/components/image-dialog/image-dialog';
import { first, switchMap, map } from 'rxjs/operators';
import { forkJoin } from 'rxjs';
import { CustomFieldService } from '../../../settings/services/custom-field.service';
import { CustomField } from '../../../settings/models/custom-field.model';
import { NotificationService } from '../../../core/services/notification.service';

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
    ImageDialogComponent, // Required for dynamic dialog usage with MatDialog
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

  constructor(
    private fb: FormBuilder,
    private productService: ProductService,
    private router: Router,
    private route: ActivatedRoute,
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
    this.customFieldService.getCustomFields().subscribe(fields => {
      this.customFields = fields;
      this.addCustomFieldControls();
    });

    const idParam = this.route.snapshot.params['id'];
    const navigation = this.router.getCurrentNavigation();
    const navigationState = navigation?.extras?.state;

    if (navigationState && navigationState['productData']) {
      const productData = navigationState['productData'];
      const patchData: { [key: string]: any } = {};

      // Extract only the top-level properties that match form controls
      Object.keys(this.productForm.controls).forEach(key => {
        if (productData.hasOwnProperty(key)) {
          patchData[key] = productData[key];
        }
      });

      this.productForm.patchValue(patchData);
    }

    if (idParam) {
      this.isEditMode = true;
      this.productId = +idParam;
      this.productService.products$.pipe(first()).subscribe((products: Product[]) => {
        const product = products.find(p => p.id === this.productId);
        if (product) {
          this.product = product;
          this.productForm.patchValue(product);
          this.patchCustomFieldValues();
        }
      });
    }
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

  getImageUrl(imagePath: string): string {
    // Backend serves images from the 'uploads/product_images' directory.
    return `/uploads/product_images/${imagePath}`;
  }

  removeStagedImage(index: number): void {
    this.stagedImages.splice(index, 1);
    this.stagedImagePreviews.splice(index, 1);
  }

  updateImageDetails(imageId: number, field: 'title' | 'description', event: Event): void {
    if (this.productId && this.product && this.product.images) {
      const input = event.target as HTMLInputElement;
      const value = input.value;
      this.productService.updateProductImage(this.productId, imageId, { [field]: value }).subscribe(() => {
        // Update the local product object for a more responsive UI
        const image = this.product?.images?.find(img => img.id === imageId);
        if (image) {
          image[field] = value;
        }
        this.notificationService.showSuccess('Image details updated.');
      });
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) {
      if (this.isEditMode && this.productId) {
        // Handle multiple file uploads in edit mode
        Array.from(input.files).forEach(file => {
          this.productService.uploadProductImage(this.productId!, file).subscribe((newImage) => {
            if (this.product && this.product.images) {
              this.product.images.push(newImage);
            }
          });
        });
      } else {
        // Handle staging multiple files in create mode
        Array.from(input.files).forEach(file => {
          this.stagedImages.push(file);
          const reader = new FileReader();
          reader.onload = (e) => {
            // Ensure the event target is not null and has a result
            if (e.target?.result) {
              this.stagedImagePreviews.push(e.target.result as string);
            }
          };
          reader.onerror = (e) => {
            console.error('Error reading file:', e);
          };
          reader.readAsDataURL(file);
        });
      }
    }
  }

  openImageDialog(image: ProductImage): void {
    if (!this.productId) return;
    
    const dialogRef = this.dialog.open(ImageDialogComponent, {
      width: '500px',
      data: { image: image, productId: this.productId }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        // Update the local product images with the updated image
        if (this.product && this.product.images) {
          const index = this.product.images.findIndex(img => img.id === result.id);
          if (index !== -1) {
            this.product.images[index] = result;
          }
        }
      }
    });
  }

  deleteImage(event: Event, imageId: number): void {
    event.stopPropagation(); // Prevent opening the dialog when deleting
    if (this.productId) {
      this.productService.deleteProductImage(this.productId, imageId).subscribe(() => {
        if (this.product && this.product.images) {
          const index = this.product.images.findIndex(img => img.id === imageId);
          if (index > -1) {
            this.product.images.splice(index, 1);
          }
        }
        this.notificationService.showSuccess('Image deleted.');
      });
    }
  }

  setPrimaryImage(event: Event, imageId: number): void {
    event.stopPropagation(); // Prevent opening the dialog when setting primary
    if (this.productId) {
      this.productService.setPrimaryProductImage(this.productId, imageId).subscribe(() => {
        if (this.product && this.product.images) {
          this.product.images.forEach(img => {
            img.is_primary = img.id === imageId ? 1 : 0;
          });
        }
        this.notificationService.showSuccess('Primary image set.');
      });
    }
  }

  onSubmit(): void {
    if (this.productForm.invalid) {
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
      const productToUpdate: Product = { id: this.productId, ...productData };
      this.productService.updateProduct(productToUpdate).pipe(
        switchMap(() => this.productService.saveCustomFieldValues(this.productId!, customFieldValues))
      ).subscribe(() => {
        this.router.navigate(['/products']);
      });
    } else {
      this.productService.createProduct(productData).pipe(
        switchMap(newProduct => {
          const customFields$ = this.productService.saveCustomFieldValues(newProduct.id, customFieldValues);
          
          // Handle image uploads - create an observable for each staged image
          const imageUploads$ = this.stagedImages.map(file => 
            this.productService.uploadProductImage(newProduct.id, file)
          );
          
          // If there are no image uploads, just save custom fields
          if (imageUploads$.length === 0) {
            return customFields$;
          }
          
          // Combine custom field saving and image uploads
          return forkJoin([customFields$, ...imageUploads$]).pipe(
            map(() => newProduct) // Pass the newProduct through
          );
        })
      ).subscribe((newProduct) => {
        this.router.navigate(['/products', newProduct.id, 'edit']);
      });
    }
  }

  onCancel(): void {
    this.router.navigate(['/products']);
  }
}
