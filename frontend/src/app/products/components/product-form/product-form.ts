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
import { first } from 'rxjs';

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
  ],
})
export class ProductForm implements OnInit {
  productForm: FormGroup;
  isEditMode = false;
  product: Product | null = null;
  private productId: number | null = null;

  constructor(
    private fb: FormBuilder,
    private productService: ProductService,
    private router: Router,
    private route: ActivatedRoute
  ) {
    this.productForm = this.fb.group({
      name: ['', Validators.required],
      sku: ['', Validators.required],
      description: [''],
      default_resale_price: [0, [Validators.required, Validators.min(0)]]
    });
  }

  ngOnInit(): void {
    const idParam = this.route.snapshot.params['id'];
    const navigationState = this.router.getCurrentNavigation()?.extras.state;

    if (navigationState && navigationState['productData']) {
      this.productForm.patchValue(navigationState['productData']);
    }

    if (idParam) {
      this.isEditMode = true;
      this.productId = +idParam;
      this.productService.products$.pipe(first()).subscribe(products => {
        const product = products.find(p => p.id === this.productId);
        if (product) {
          this.product = product;
          this.productForm.patchValue(product);
        }
      });
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.length && this.productId) {
      const file = input.files[0];
      this.productService.uploadProductImage(this.productId, file).subscribe(() => {
        // Refresh the product data to show the new image
        this.productService.getProducts();
      });
    }
  }

  deleteImage(imageId: number): void {
    if (this.productId) {
      this.productService.deleteProductImage(this.productId, imageId).subscribe(() => {
        this.productService.getProducts();
      });
    }
  }

  setPrimaryImage(imageId: number): void {
    if (this.productId) {
      this.productService.setPrimaryProductImage(this.productId, imageId).subscribe(() => {
        this.productService.getProducts();
      });
    }
  }

  onSubmit(): void {
    if (this.productForm.invalid) {
      return;
    }

    const productData = this.productForm.value;

    if (this.isEditMode && this.productId) {
      const productToUpdate: Product = { id: this.productId, ...productData };
      this.productService.updateProduct(productToUpdate).subscribe(() => {
        this.router.navigate(['/products']);
      });
    } else {
      this.productService.createProduct(productData).subscribe(() => {
        this.router.navigate(['/products']);
      });
    }
  }

  onCancel(): void {
    this.router.navigate(['/products']);
  }
}
