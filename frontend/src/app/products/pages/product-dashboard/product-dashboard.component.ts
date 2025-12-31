
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule } from '@angular/router';
import { Observable, map } from 'rxjs';
import { DashboardStatsService, DashboardStats } from '../../../dashboard/services/dashboard-stats.service';
import { StatCardComponent } from '../../../dashboard/widgets/stat-card/stat-card.component';
import { InventoryHealthWidgetComponent } from '../../../dashboard/widgets/inventory-health-widget/inventory-health-widget.component';
import { ScreenService } from '../../../core/services/screen.service';

@Component({
    selector: 'app-product-dashboard',
    standalone: true,
    imports: [
        CommonModule,
        MatButtonModule,
        MatIconModule,
        RouterModule,
        StatCardComponent,
        InventoryHealthWidgetComponent
    ],
    template: `
    <div class="product-dashboard px-4 pt-2 relative z-10">
      <ng-container *ngIf="stats$ | async as stats">
        <!-- KPI Cards Row - Marketing Style -->
        <div class="kpi-cards">
            <app-stat-card 
                title="Products" 
                [value]="stats.totalProducts" 
                icon="inventory_2" 
                colorType="primary"
                link="/products">
            </app-stat-card>
            
            <app-stat-card 
                title="Inventory Value" 
                [value]="(stats.totalInventoryValue | currency:'USD':'symbol':'1.0-0') ?? ''" 
                icon="payments" 
                colorType="success"
                link="/products">
            </app-stat-card>

            <app-stat-card 
                title="Low Stock" 
                [value]="stats.lowStockCount" 
                icon="warning" 
                colorType="warn"
                link="/products">
            </app-stat-card>

            <app-stat-card 
                title="Stock Health" 
                [value]="stats.stockHealthPercentage + '%'" 
                icon="health_and_safety" 
                colorType="accent"
                link="/products">
            </app-stat-card>
        </div>

        <div class="widgets-row">
            <app-inventory-health-widget 
                class="widget-lg" 
                title="Low Stock Alerts"
                [products]="stats.lowStockProducts">
            </app-inventory-health-widget>
            
            <div class="placeholder-widget">
                <div class="text-center">
                    <div class="placeholder-icon">
                        <mat-icon>bar_chart</mat-icon>
                    </div>
                    <p class="placeholder-title">Category Breakdown</p>
                    <p class="placeholder-subtitle">Coming Soon</p>
                </div>
            </div>
        </div>
      </ng-container>
    </div>
  `,
    styles: [`
    :host { display: block; }

    .kpi-cards {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
    }

    .widgets-row {
        display: grid;
        grid-template-columns: 2fr 1fr;
        gap: 16px;
    }

    .widget-lg {
        min-height: 200px;
    }

    .placeholder-widget {
        min-height: 200px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: var(--border-radius);
        border: 1px dashed var(--border-color);
        background: var(--bg-app);
        color: var(--text-hint);
    }

    .placeholder-icon {
        background: var(--bg-card);
        padding: 12px;
        border-radius: 50%;
        display: inline-flex;
        margin-bottom: 8px;
        box-shadow: var(--shadow-sm);
    }

    .placeholder-icon mat-icon {
        color: var(--text-hint);
    }

    .placeholder-title {
        font-weight: 500;
        font-size: 0.9rem;
        margin: 0;
    }

    .placeholder-subtitle {
        font-size: 0.75rem;
        margin: 4px 0 0;
    }

    @media (max-width: 768px) {
        .widgets-row {
            grid-template-columns: 1fr;
        }
    }
  `]
})
export class ProductDashboardComponent implements OnInit {
    stats$!: Observable<DashboardStats>;

    constructor(
        private statsService: DashboardStatsService,
        public screen: ScreenService
    ) { }

    ngOnInit() {
        this.stats$ = this.statsService.getStats();
    }
}
