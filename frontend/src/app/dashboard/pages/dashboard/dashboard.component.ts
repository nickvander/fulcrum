import { Component, OnInit } from '@angular/core';
import { DashboardStats, DashboardStatsService } from '../../services/dashboard-stats.service';
import { Observable } from 'rxjs';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { KpiCardComponent } from '../../widgets/kpi-card/kpi-card.component';
import { LowStockListWidgetComponent } from '../../widgets/low-stock-list/low-stock-list.component';
import { InventoryHealthWidgetComponent } from '../../widgets/inventory-health-widget/inventory-health-widget.component';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterModule } from '@angular/router';

@Component({
    selector: 'app-dashboard',
    templateUrl: './dashboard.component.html',
    styleUrls: ['./dashboard.component.scss'],
    standalone: true,
    imports: [
        CommonModule,
        MatButtonModule,
        MatIconModule,
        MatTooltipModule,
        MatProgressSpinnerModule,
        KpiCardComponent,
        LowStockListWidgetComponent,
        InventoryHealthWidgetComponent,
        RouterModule
    ]
})
export class DashboardComponent implements OnInit {
    stats$!: Observable<DashboardStats>;

    constructor(private statsService: DashboardStatsService) { }

    ngOnInit(): void {
        this.refresh();
    }

    refresh(): void {
        this.stats$ = this.statsService.getStats();
    }
}
