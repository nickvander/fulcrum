import { Component, OnInit } from '@angular/core';
import { DashboardStats, DashboardStatsService } from '../../services/dashboard-stats.service';
import { finalize, Observable } from 'rxjs';
import { LaunchReadinessReport, LaunchReadinessSection, OnboardingService, OnboardingStatus } from '../../services/onboarding.service';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
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
        MatSnackBarModule,
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
    launchReadiness$!: Observable<LaunchReadinessReport>;
    creatingDemoWorkspace = false;

    constructor(
        private statsService: DashboardStatsService,
        private onboardingService: OnboardingService,
        private snackBar: MatSnackBar
    ) { }

    ngOnInit(): void {
        this.refresh();
    }

    refresh(): void {
        this.stats$ = this.statsService.getStats();
        this.onboardingStatus$ = this.onboardingService.getStatus();
        this.launchReadiness$ = this.onboardingService.getLaunchReadiness();
    }

    createDemoWorkspace(): void {
        if (this.creatingDemoWorkspace) return;

        this.creatingDemoWorkspace = true;
        this.onboardingService.createDemoWorkspace()
            .pipe(finalize(() => this.creatingDemoWorkspace = false))
            .subscribe({
                next: (result) => {
                    this.snackBar.open(result.message, 'Close', { duration: 5000 });
                    this.refresh();
                },
                error: () => {
                    this.snackBar.open(
                        'Demo workspace could not be created. Please try again.',
                        'Close',
                        { duration: 5000 }
                    );
                }
            });
    }

    readinessIcon(section: LaunchReadinessSection): string {
        if (section.status === 'ready') return 'check_circle';
        if (section.status === 'needs_attention') return 'warning';
        if (section.status === 'optional') return 'radio_button_unchecked';
        return 'error';
    }
}
