import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';

@Component({
  selector: 'app-store-product',
  standalone: true,
  imports: [CommonModule, RouterModule, MatButtonModule, MatCardModule],
  template: `
    <div class="store-container">
      <mat-card>
        <mat-card-header>
           <mat-card-title>Fulcrum Store</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <div class="placeholder-content">
            <h2>Product #{{ productId }}</h2>
            <p>Our online store is coming soon!</p>
            <p>If you are an administrator, please log in to manage this product.</p>
          </div>
        </mat-card-content>
        <mat-card-actions align="end">
          <a mat-button color="primary" [routerLink]="['/login']" [queryParams]="{ returnUrl: '/products/' + productId }">Login to Manage</a>
        </mat-card-actions>
      </mat-card>
    </div>
  `,
  styles: [`
    .store-container {
      display: flex;
      justify-content: center;
      padding-top: 48px;
    }
    mat-card {
      max-width: 400px;
      width: 100%;
      margin: 16px;
    }
    .placeholder-content {
      padding: 24px 0;
      text-align: center;
    }
    h2 { margin-top: 0; }
  `]
})
export class StoreProductComponent implements OnInit {
  productId: string | null = null;

  constructor(private route: ActivatedRoute) { }

  ngOnInit(): void {
    this.productId = this.route.snapshot.paramMap.get('id');
  }
}
