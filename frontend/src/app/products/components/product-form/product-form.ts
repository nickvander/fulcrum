import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ProductService } from '../../services/product';
import { Product } from '../../models/product.model';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { first, switchMap, map } from 'rxjs/operators';
import { forkJoin } from 'rxjs';
import { CustomFieldService } from '../../../settings/services/custom-field.service';
import { CustomField } from '../../../settings/models/custom-field.model';

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
  ],
})
export class ProductForm implements OnInit {
  productForm: FormGroup;
  isEditMode = false;
  product: Product | null = null;
  private productId: number | null = null;
  customFields: CustomField[] = [];
  stagedImages: File[] = [];
  stagedImagePreviews: string[] = [];

  constructor(
    private fb: FormBuilder,
    private productService: ProductService,
    private router: Router,
    private route: ActivatedRoute,
    private customFieldService: CustomFieldService
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
    // Assuming the backend serves images from an 'uploads' directory at the root
    return `/uploads/${imagePath}`;
  }

  removeStagedImage(index: number): void {
    this.stagedImages.splice(index, 1);
    this.stagedImagePreviews.splice(index, 1);
  }

  updateImageDetails(imageId: number, field: 'title' | 'description', event: Event): void {
    if (this.productId) {
      const input = event.target as HTMLInputElement;
      const value = input.value;
      this.productService.updateProductImage(this.productId, imageId, { [field]: value }).subscribe(() => {
        this.productService.getProducts().subscribe();
      });
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) {
      const file = input.files[0];
      if (this.isEditMode && this.productId) {
        this.productService.uploadProductImage(this.productId, file).subscribe(() => {
          // Refresh the product data to show the new image
          this.productService.getProducts().subscribe();
        });
      } else {
        this.stagedImages.push(file);
        const reader = new FileReader();
        reader.onload = () => {
          this.stagedImagePreviews.push(reader.result as string);
        };
        reader.readAsDataURL(file);
      }
    }
  }

  deleteImage(imageId: number): void {
    if (this.productId) {
      this.productService.deleteProductImage(this.productId, imageId).subscribe(() => {
        this.productService.getProducts().subscribe();
      });
    }
  }

  setPrimaryImage(imageId: number): void {
    if (this.productId) {
      this.productService.setPrimaryProductImage(this.productId, imageId).subscribe(() => {
        this.productService.getProducts().subscribe();
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
          const imageUploads$ = this.stagedImages.map(file => this.productService.uploadProductImage(newProduct.id, file));
          
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
