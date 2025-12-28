import { Component, Input } from '@angular/core';
import { Product } from '../../../products/models/product.model';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-low-stock-list',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    RouterModule
  ],
  template: `
    <mat-card class="h-full shadow-sm rounded-xl border-none overflow-hidden">
      <mat-card-header class="pb-2">
        <mat-card-title class="flex justify-between items-center w-full">
          <span class="text-lg font-bold">Critical Low Stock</span>
          <button mat-button color="primary" routerLink="/products">View All</button>
        </mat-card-title>
      </mat-card-header>
      <mat-card-content>
        <div *ngIf="products.length === 0" class="flex flex-col items-center justify-center py-8 text-gray-400">
          <mat-icon class="text-48 mb-2">check_circle_outline</mat-icon>
          <p>All stock levels healthy</p>
        </div>
        
        <mat-list *ngIf="products.length > 0">
          <mat-list-item *ngFor="let product of products" class="hover:bg-gray-50 transition-colors">
            <mat-icon matListItemIcon class="text-red-500">error_outline</mat-icon>
            <div matListItemTitle class="font-medium">{{ product.name }}</div>
            <div matListItemLine class="text-xs text-gray-500">SKU: {{ product.sku }}</div>
            <div matListItemMeta class="text-red-600 font-bold">
              {{ getTotalStock(product) }} units
            </div>
          </mat-list-item>
        </mat-list>
      </mat-card-content>
    </mat-card>
  `,
  styles: [`
    :host { display: block; height: 100%; }
    .text-48 { font-size: 48px; width: 48px; height: 48px; }
    .text-red-500 { color: #ef4444; }
    .text-red-600 { color: #dc2626; }
    .hover\:bg-gray-50:hover { background-color: #f9fafb; }
    .transition-colors { transition: background-color 0.2s ease; }
    .text-lg { font-size: 1.125rem; }
  `]
})
export class LowStockListWidgetComponent {
  @Input() products: Product[] = [];

  getTotalStock(product: Product): number {
    return product.inventory_items?.reduce((acc, item) => acc + item.quantity, 0) || 0;
  }
}
