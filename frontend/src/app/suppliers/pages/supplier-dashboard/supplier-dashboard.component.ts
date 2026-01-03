
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatListModule } from '@angular/material/list';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule } from '@ngneat/transloco';
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
        StatCardComponent,
        TranslocoModule
    ],
    templateUrl: './supplier-dashboard.component.html',
    styleUrls: ['./supplier-dashboard.component.scss']
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
