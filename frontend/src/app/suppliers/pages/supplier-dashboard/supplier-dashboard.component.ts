
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatListModule } from '@angular/material/list';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Observable, forkJoin, map } from 'rxjs';
import { SuppliersService } from '../../suppliers.service';
import { StatCardComponent } from '../../../dashboard/widgets/stat-card/stat-card.component';
import { PurchaseOrder, PurchaseOrderStatus } from '../../../shared/models/purchase-order.model';
import { Supplier } from '../../../shared/models/supplier.model';
import { ScreenService } from '../../../core/services/screen.service';

interface SupplierStats {
    totalSuppliers: number;
    activePos: number;
    overduePos: number;
    totalSpend: number;
    recentPos: PurchaseOrder[];
    topSuppliers: Supplier[];
}

@Component({
    selector: 'app-supplier-dashboard',
    standalone: true,
    imports: [
        CommonModule,
        MatButtonModule,
        MatIconModule,
        RouterModule,
        MatCardModule,
        MatListModule,
        MatTooltipModule,
        StatCardComponent
    ],
    template: `
    <div class="supplier-dashboard px-4 pt-2">
      <ng-container *ngIf="stats$ | async as stats; else loading">
        <!-- KPI Cards Row - Marketing Style -->
        <div class="kpi-cards">
            <app-stat-card 
                title="Suppliers" 
                [value]="stats.totalSuppliers" 
                icon="business" 
                colorType="primary"
                link="/suppliers">
            </app-stat-card>
            
            <app-stat-card 
                title="Active POs" 
                [value]="stats.activePos" 
                icon="shopping_cart" 
                colorType="warn"
                link="/suppliers/po">
            </app-stat-card>

            <app-stat-card 
                title="Total Spend" 
                [value]="(stats.totalSpend | currency:'USD':'symbol':'1.0-0') ?? ''" 
                icon="receipt_long" 
                colorType="success">
            </app-stat-card>

            <app-stat-card 
                title="Overdue" 
                [value]="stats.overduePos" 
                icon="warning" 
                colorType="error"
                link="/suppliers/po">
            </app-stat-card>
        </div>

        <div class="widgets-row">
            <!-- Recent POs Widget -->
            <div class="widget-card">
                <div class="widget-header">
                    <h3>Recent Purchase Orders</h3>
                    <a mat-button color="primary" routerLink="/suppliers/po">View All</a>
                </div>
                <div class="widget-content">
                    <mat-nav-list class="dense-list">
                        <a mat-list-item *ngFor="let po of stats.recentPos" [routerLink]="['/suppliers/po', po.id]"
                           class="list-item">
                            <span matListItemIcon class="icon-badge primary">
                                <mat-icon>description</mat-icon>
                            </span>
                            <span matListItemTitle>PO #{{po.id}} | {{po.supplier_name}}</span>
                            <span matListItemLine class="list-meta">
                                <span>{{po.total_amount | currency}}</span>
                                <span class="status-badge" 
                                      [class.status-ordered]="po.status === 'ordered'"
                                      [class.status-completed]="po.status === 'completed'"
                                      [class.status-draft]="po.status === 'draft'">
                                    {{po.status}}
                                </span>
                            </span>
                        </a>
                        <div *ngIf="stats.recentPos.length === 0" class="empty-widget">
                            <mat-icon>inbox</mat-icon>
                            <span>No recent orders</span>
                        </div>
                    </mat-nav-list>
                </div>
            </div>
            
            <!-- Top Suppliers Widget -->
            <div class="widget-card">
                <div class="widget-header">
                    <h3>Top Suppliers</h3>
                    <a mat-button color="primary" routerLink="/suppliers">View All</a>
                </div>
                <div class="widget-content">
                     <mat-nav-list class="dense-list">
                        <a mat-list-item *ngFor="let supplier of stats.topSuppliers" [routerLink]="['/suppliers/id', supplier.id]"
                           class="list-item">
                            <span matListItemIcon class="icon-badge accent">
                                <mat-icon>business</mat-icon>
                            </span>
                            <span matListItemTitle>{{supplier.name}}</span>
                             <span matListItemLine class="list-meta">
                                <span>{{supplier.contact_person || 'No contact'}}</span>
                                <span class="orders-count">{{supplier.po_count}} Orders</span>
                            </span>
                        </a>
                         <div *ngIf="stats.topSuppliers.length === 0" class="empty-widget">
                            <mat-icon>business_off</mat-icon>
                            <span>No supplier data</span>
                        </div>
                     </mat-nav-list>
                </div>
            </div>
        </div>
      </ng-container>

      <ng-template #loading>
        <div class="loading-spinner">
             <div class="spinner"></div>
        </div>
      </ng-template>
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
        grid-template-columns: 1fr 1fr;
        gap: 16px;
    }

    .widget-card {
        background: var(--bg-card);
        border-radius: var(--border-radius);
        border: 1px solid var(--border-color);
        box-shadow: var(--shadow-sm);
        overflow: hidden;
        display: flex;
        flex-direction: column;
        min-height: 240px;
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

    .dense-list {
        padding-top: 0;
    }

    .list-item {
        border-bottom: 1px solid var(--border-color);
    }

    .list-item:last-child {
        border-bottom: none;
    }

    .icon-badge {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 12px;
    }

    .icon-badge.primary {
        background: var(--info-bg);
        color: var(--info-color);
    }

    .icon-badge.accent {
        background: #f3e8ff;
        color: #7c3aed;
    }

    .icon-badge mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
    }

    .list-meta {
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
        color: var(--text-secondary);
    }

    .status-badge {
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
    }

    .status-ordered {
        background: var(--info-bg);
        color: var(--info-color);
    }

    .status-completed {
        background: var(--success-bg);
        color: var(--success-color);
    }

    .status-draft {
        background: var(--warning-bg);
        color: var(--warning-color);
    }

    .orders-count {
        font-weight: 600;
        color: var(--text-main);
    }

    .empty-widget {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 32px;
        color: var(--text-hint);
    }

    .empty-widget mat-icon {
        font-size: 32px;
        width: 32px;
        height: 32px;
        margin-bottom: 8px;
    }

    .loading-spinner {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 200px;
    }

    .spinner {
        width: 24px;
        height: 24px;
        border: 3px solid var(--border-color);
        border-top-color: var(--primary-color);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    @media (max-width: 768px) {
        .widgets-row {
            grid-template-columns: 1fr;
        }
    }

    ::ng-deep .dense-list .mat-mdc-list-item {
        height: auto !important;
        min-height: 56px;
    }
  `]
})
export class SupplierDashboardComponent implements OnInit {
    stats$!: Observable<SupplierStats>;

    constructor(
        private suppliersService: SuppliersService,
        public screen: ScreenService
    ) { }

    ngOnInit() {
        this.stats$ = forkJoin({
            suppliers: this.suppliersService.getSuppliers(0, 100),
            pos: this.suppliersService.getPurchaseOrders(0, 100)
        }).pipe(
            map(({ suppliers, pos }) => {
                const activePos = pos.filter(po => po.status === PurchaseOrderStatus.ORDERED || po.status === PurchaseOrderStatus.PARTIALLY_RECEIVED);

                const overduePos = activePos.filter(po => {
                    const date = new Date(po.created_at);
                    const thirtyDaysAgo = new Date();
                    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
                    return date < thirtyDaysAgo;
                }).length;

                const totalSpend = pos.reduce((sum, po) => sum + (po.total_amount || 0), 0);
                const topSuppliers = [...suppliers].sort((a, b) => (b.po_count || 0) - (a.po_count || 0)).slice(0, 5);
                const recentPos = [...pos].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 5);

                return {
                    totalSuppliers: suppliers.length,
                    activePos: activePos.length,
                    overduePos,
                    totalSpend,
                    recentPos,
                    topSuppliers
                };
            })
        );
    }
}
