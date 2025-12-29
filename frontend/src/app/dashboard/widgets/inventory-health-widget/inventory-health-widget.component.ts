
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatProgressBarModule } from '@angular/material/progress-bar';
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
        RouterModule
    ],
    template: `
    <mat-card class="dashboard-card">
      <mat-card-header>
        <mat-card-title>Inventory Health</mat-card-title>
        <mat-card-subtitle>Items needing attention</mat-card-subtitle>
      </mat-card-header>
      <mat-card-content>
        <div *ngIf="loading" class="loading-state">
            <mat-progress-bar mode="indeterminate"></mat-progress-bar>
        </div>
        
        <div *ngIf="!loading && lowStockItems.length === 0" class="empty-state">
            <mat-icon>check_circle</mat-icon>
            <p>All stock levels look good!</p>
        </div>

        <mat-list *ngIf="!loading && lowStockItems.length > 0">
            <mat-list-item *ngFor="let item of lowStockItems">
                <span matListItemIcon class="status-icon warn">
                    <mat-icon color="warn">warning</mat-icon>
                </span>
                <span matListItemTitle>{{item.name}}</span>
                <span matListItemLine>
                    <ng-container *ngIf="(item.stock_quantity || 0) < (item.low_stock_quantity_threshold || 10); else dayAlert">
                        <strong class="warn-text">Low Quantity: {{item.stock_quantity || 0}} units</strong> 
                        (Threshold: {{item.low_stock_quantity_threshold || 10}})
                    </ng-container>
                    <ng-template #dayAlert>
                        <strong class="warn-text">{{item.days_of_inventory | number:'1.0-0'}} Days Left</strong> 
                        ({{item.stock_quantity || 0}} units)
                    </ng-template>
                </span>
                <span matListItemMeta>
                     <button mat-icon-button color="primary" [routerLink]="['/suppliers/po/create']" [queryParams]="{product_id: item.id}">
                        <mat-icon>add_shopping_cart</mat-icon>
                     </button>
                </span>
            </mat-list-item>
        </mat-list>
      </mat-card-content>
      <mat-card-actions align="end">
        <button mat-button color="primary" routerLink="/products">View All Products</button>
      </mat-card-actions>
    </mat-card>
  `,
    styles: [`
    .dashboard-card {
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    .status-icon.warn {
        color: #f44336;
    }
    .empty-state {
        text-align: center;
        padding: 20px;
        color: #757575;
    }
    .empty-state mat-icon {
        font-size: 48px;
        height: 48px;
        width: 48px;
        margin-bottom: 8px;
        color: #4caf50;
    }
    mat-card-content {
        flex-grow: 1;
        overflow-y: auto;
    }
    .warn-text {
        color: #d32f2f;
        font-weight: 500;
    }
  `]
})
export class InventoryHealthWidgetComponent implements OnInit {
    lowStockItems: Product[] = [];
    loading = true;

    constructor(private productService: ProductService) { }

    ngOnInit(): void {
        this.loadData();
    }

    loadData() {
        this.loading = true;

        // Using existing getProducts.
        this.productService.getProducts(1, 100).subscribe(response => {
            this.lowStockItems = response.data
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

            this.loading = false;
        });
    }
}
