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
  ],
})
export class ProductForm implements OnInit {
  productForm: FormGroup;
  isEditMode = false;
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
    this.productId = this.route.snapshot.params['id'];
    if (this.productId) {
      this.isEditMode = true;
      // TODO: Implement getProductById in service
      // this.productService.getProductById(this.productId).subscribe(product => {
      //   this.productForm.patchValue(product);
      // });
    }
  }

  onSubmit(): void {
    if (this.productForm.valid) {
      const productData: Product = this.productForm.value;
      if (this.isEditMode && this.productId) {
        // TODO: Implement updateProduct in service
        // this.productService.updateProduct(this.productId, productData).subscribe(() => {
        //   this.router.navigate(['/products']);
        // });
        console.log('Update product:', this.productId, productData);
        this.router.navigate(['/products']);
      } else {
        // TODO: Implement createProduct in service
        // this.productService.createProduct(productData).subscribe(() => {
        //   this.router.navigate(['/products']);
        // });
        console.log('Create product:', productData);
        this.router.navigate(['/products']);
      }
    }
  }

  onCancel(): void {
    this.router.navigate(['/products']);
  }
}
