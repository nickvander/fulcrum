import { Component, ViewChild, OnInit } from '@angular/core';
import { MatSidenav } from '@angular/material/sidenav';
import { Product } from '../../models/product.model';
import { ProductService } from '../../services/product';
import { ProductList } from '../product-list/product-list';
import { ProductForm } from '../product-form/product-form';
import { CommonModule } from '@angular/common';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-products',
  templateUrl: './products.html',
  styleUrls: ['./products.scss'],
  standalone: true,
  imports: [
    CommonModule,
    MatSidenavModule,
    MatButtonModule,
    MatIconModule,
    ProductList,
    ProductForm
  ]
})
export class ProductsComponent implements OnInit {
  @ViewChild('sidenav') sidenav!: MatSidenav;
  
  selectedProduct: Product | null = null;
  isEditing = false;

  constructor(private productService: ProductService) {}

  ngOnInit(): void {
    // Initialize the product list
    this.productService.getProducts().subscribe();
  }

  openEditPanel(product: Product): void {
    this.selectedProduct = product;
    this.isEditing = true;
    setTimeout(() => {  // Use setTimeout to ensure sidenav is rendered
      this.sidenav?.open();
    }, 0);
  }
  
  openAddPanel(): void {
    // For adding, we pass a minimal product object
    this.selectedProduct = {
      id: 0, // Will be ignored for new products
      name: '',
      sku: '',
      description: '',
      default_resale_price: 0,
      cost_price: 0,
      images: [],
      custom_fields: []
    } as Product;
    this.isEditing = false;
    setTimeout(() => {  // Use setTimeout to ensure sidenav is rendered
      this.sidenav?.open();
    }, 0);
  }

  closeEditPanel(): void {
    this.sidenav?.close();
    this.selectedProduct = null;
    this.isEditing = false;
  }

  onProductSaved(): void {
    // Refresh the product list after saving
    this.productService.getProducts().subscribe();
    this.closeEditPanel();
  }
}