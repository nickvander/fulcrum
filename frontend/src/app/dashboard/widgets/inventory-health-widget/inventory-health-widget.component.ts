
import { Component, OnInit, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ProductService } from '../../../products/services/product';
import { Product } from '../../../products/models/product.model';
import { RouterModule } from '@angular/router';

@Component({
    selector: 'app-inventory-health-widget',
    standalone: true,
    imports: [
        CommonModule,
        MatCardModule,
        MatButtonModule,
        MatIconModule,
        MatListModule,
        MatProgressBarModule,
        MatProgressSpinnerModule,
        MatTooltipModule,
        RouterModule
    ],
    template: `
    <div class="widget-container">
      <div class="widget-header">
        <h3>{{ title }}</h3>
        <a mat-button color="primary" routerLink="/products">View All</a>
      </div>
      
      <div class="widget-content">
        <div *ngIf="loading" class="loading-state">
            <mat-spinner diameter="30"></mat-spinner>
        </div>
        
        <div *ngIf="!loading && lowStockItems.length === 0" class="empty-state">
            <mat-icon class="success-icon">check_circle</mat-icon>
            <p>All inventory levels healthy</p>
        </div>

        <mat-nav-list *ngIf="!loading && lowStockItems.length > 0" class="dense-list">
            <a mat-list-item *ngFor="let item of lowStockItems" 
               [routerLink]="['/products']" [queryParams]="{open_sku: item.sku}"
               class="list-item">
                <span matListItemIcon class="icon-badge" [class.warning]="!isQtyLow(item)" [class.error]="isQtyLow(item)">
                    <mat-icon>warning</mat-icon>
                </span>
                <span matListItemTitle class="item-name">{{item.name}}</span>
                <span matListItemLine class="item-meta">
                    <ng-container *ngIf="isQtyLow(item); else dayAlert">
                        <span class="stock-badge critical">{{item.stock_quantity || 0}} units</span>
                        <span>(Min: {{item.low_stock_quantity_threshold || 10}})</span>
                    </ng-container>
                    <ng-template #dayAlert>
                        <span class="stock-badge warning">{{item.days_of_inventory | number:'1.0-0'}} Days</span>
                        <span>({{item.stock_quantity || 0}} units)</span>
                    </ng-template>
                </span>
                <span matListItemMeta>
                     <button mat-icon-button color="primary" [routerLink]="['/suppliers/po/create']" [queryParams]="{product_id: item.id}" 
                             (click)="$event.stopPropagation()" matTooltip="Order Stock" class="action-btn">
                        <mat-icon>add_shopping_cart</mat-icon>
                     </button>
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

    .loading-state {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 32px;
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

    .icon-badge.warning {
        background: var(--warning-bg);
        color: var(--warning-color);
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
        gap: 8px;
        font-size: 0.7rem;
        color: var(--text-secondary);
    }

    .stock-badge {
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 4px;
    }

    .stock-badge.warning {
        background: var(--warning-bg);
        color: var(--warning-color);
    }

    .stock-badge.critical {
        background: var(--error-bg);
        color: var(--error-color);
    }

    .action-btn {
        transform: scale(0.8);
        color: var(--info-color);
    }
  `]
})
export class InventoryHealthWidgetComponent implements OnInit {
    @Input() products: Product[] | null = null;
    @Input() title: string = 'Inventory Health';

    lowStockItems: Product[] = [];
    loading = true;

    constructor(private productService: ProductService) { }

    ngOnInit(): void {
        this.loadData();
    }

    isQtyLow(item: Product): boolean {
        return (item.stock_quantity || 0) < (item.low_stock_quantity_threshold || 10);
    }

    loadData() {
        this.loading = true;

        if (this.products) {
            this.processProducts(this.products);
            this.loading = false;
        } else {
            this.productService.getProducts(1, 100).subscribe(response => {
                this.processProducts(response.data);
                this.loading = false;
            });
        }
    }

    private processProducts(products: Product[]) {
        this.lowStockItems = products
            .map(p => ({
                ...p,
                days_of_inventory: p.days_of_inventory !== undefined ? p.days_of_inventory : 0
            }))
            .filter(p => {
                const daysLow = p.days_of_inventory !== undefined && p.days_of_inventory < (p.low_inventory_threshold || 30) && p.days_of_inventory >= 0;
                const qtyLow = (p.stock_quantity || 0) < (p.low_stock_quantity_threshold || 10);
                return daysLow || qtyLow;
            })
            .sort((a, b) => (a.days_of_inventory || 0) - (b.days_of_inventory || 0))
            .slice(0, 5);
    }
}
