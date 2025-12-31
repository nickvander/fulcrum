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
    <div class="widget-container">
      <div class="widget-header">
        <h3>Critical Low Stock</h3>
        <a mat-button color="primary" routerLink="/products" [queryParams]="{max_stock: 10}">View All</a>
      </div>
      
      <div class="widget-content">
        <div *ngIf="products.length === 0" class="empty-state">
          <mat-icon class="success-icon">check_circle</mat-icon>
          <p>All stock levels healthy</p>
        </div>
        
        <mat-nav-list *ngIf="products.length > 0" class="dense-list">
          <a mat-list-item *ngFor="let product of products" 
             [routerLink]="['/products']" 
             [queryParams]="{open_sku: product.sku}"
             class="list-item">
            <span matListItemIcon class="icon-badge error">
              <mat-icon>error_outline</mat-icon>
            </span>
            <span matListItemTitle class="item-name">{{ product.name }}</span>
            <span matListItemLine class="item-meta">
              <span>SKU: {{ product.sku }}</span>
              <span class="stock-badge" [class.critical]="getTotalStock(product) === 0">
                {{ getTotalStock(product) }} units
              </span>
            </span>
          </a>
        </mat-nav-list>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; height: 100%; }

    .widget-container {
        height: 100%;
        display: flex;
        flex-direction: column;
        background: var(--bg-card);
        border-radius: var(--border-radius);
        border: 1px solid var(--border-color);
        box-shadow: var(--shadow-sm);
        overflow: hidden;
    }

    .widget-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        border-bottom: 1px solid var(--border-color);
        background: var(--bg-app);
    }

    .widget-header h3 {
        margin: 0;
        font-size: 0.9rem;
        font-weight: 600;
        color: var(--text-main);
    }

    .widget-content {
        flex: 1;
        overflow-y: auto;
    }

    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 32px;
        color: var(--text-hint);
    }

    .success-icon {
        font-size: 32px;
        width: 32px;
        height: 32px;
        color: var(--success-color);
        margin-bottom: 8px;
    }

    .empty-state p {
        margin: 0;
        font-size: 0.85rem;
    }

    .dense-list {
        padding-top: 0;
    }

    .list-item {
        border-bottom: 1px solid var(--border-color);
        height: auto !important;
        min-height: 48px;
    }

    .list-item:last-child {
        border-bottom: none;
    }

    .icon-badge {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 12px;
    }

    .icon-badge.error {
        background: var(--error-bg);
        color: var(--error-color);
    }

    .icon-badge mat-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
    }

    .item-name {
        font-size: 0.8rem;
        font-weight: 500;
        color: var(--text-main);
    }

    .item-meta {
        display: flex;
        justify-content: space-between;
        font-size: 0.7rem;
        color: var(--text-secondary);
    }

    .stock-badge {
        font-weight: 600;
        color: var(--warning-color);
    }

    .stock-badge.critical {
        color: var(--error-color);
    }
  `]
})
export class LowStockListWidgetComponent {
  @Input() products: Product[] = [];

  getTotalStock(product: Product): number {
    return product.inventory_items?.reduce((acc, item) => acc + item.quantity, 0) || 0;
  }
}
