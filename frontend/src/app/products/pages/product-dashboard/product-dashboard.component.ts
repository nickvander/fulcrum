
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
    templateUrl: './product-dashboard.component.html',
    styleUrls: ['./product-dashboard.component.scss']
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
