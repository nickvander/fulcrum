import { Component, OnInit } from '@angular/core';
import { DashboardStats, DashboardStatsService } from '../../services/dashboard-stats.service';
import { Observable } from 'rxjs';
import { OnboardingService, OnboardingStatus } from '../../services/onboarding.service';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { StatCardComponent } from '../../widgets/stat-card/stat-card.component';
import { LowStockListWidgetComponent } from '../../widgets/low-stock-list/low-stock-list.component';
import { InventoryHealthWidgetComponent } from '../../widgets/inventory-health-widget/inventory-health-widget.component';
import { OnboardingChecklistComponent } from '../../widgets/onboarding-checklist/onboarding-checklist.component';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterModule } from '@angular/router';
import { TranslocoModule } from '@ngneat/transloco';

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
        StatCardComponent,
        LowStockListWidgetComponent,
        InventoryHealthWidgetComponent,
        OnboardingChecklistComponent,
        RouterModule,
        TranslocoModule
    ]
})
export class DashboardComponent implements OnInit {
    stats$!: Observable<DashboardStats>;
    onboardingStatus$!: Observable<OnboardingStatus>;

    constructor(
        private statsService: DashboardStatsService,
        private onboardingService: OnboardingService
    ) { }

    ngOnInit(): void {
        this.refresh();
    }

    refresh(): void {
        this.stats$ = this.statsService.getStats();
        this.onboardingStatus$ = this.onboardingService.getStatus();
    }
}
