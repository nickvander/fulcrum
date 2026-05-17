import { Component, OnInit } from '@angular/core';
import { DashboardStats, DashboardStatsService } from '../../services/dashboard-stats.service';
import { LowStockReport, LowStockService } from '../../services/low-stock.service';
import { finalize, Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { SalesOrderSummary, SalesOrdersService } from '../../../sales-orders/services/sales-orders.service';
import { LaunchReadinessReport, LaunchReadinessSection, OnboardingService, OnboardingStatus } from '../../services/onboarding.service';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { StatCardComponent } from '../../widgets/stat-card/stat-card.component';
import { LowStockListWidgetComponent } from '../../widgets/low-stock-list/low-stock-list.component';
import { InventoryHealthWidgetComponent } from '../../widgets/inventory-health-widget/inventory-health-widget.component';
import { OnboardingChecklistComponent } from '../../widgets/onboarding-checklist/onboarding-checklist.component';
import { SalesByChannelWidgetComponent } from '../../widgets/sales-by-channel-widget/sales-by-channel-widget.component';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterModule } from '@angular/router';
import { TranslocoModule } from '@ngneat/transloco';
import { ConfirmationDialog, ConfirmationDialogData } from '../../../shared/components/confirmation-dialog/confirmation-dialog';

@Component({
    selector: 'app-dashboard',
    templateUrl: './dashboard.component.html',
    styleUrls: ['./dashboard.component.scss'],
    standalone: true,
    imports: [
        CommonModule,
        MatButtonModule,
        MatDialogModule,
        MatIconModule,
        MatTooltipModule,
        MatSnackBarModule,
        MatProgressSpinnerModule,
        StatCardComponent,
        LowStockListWidgetComponent,
        InventoryHealthWidgetComponent,
        OnboardingChecklistComponent,
        SalesByChannelWidgetComponent,
        RouterModule,
        TranslocoModule
    ]
})
export class DashboardComponent implements OnInit {
    stats$!: Observable<DashboardStats>;
    onboardingStatus$!: Observable<OnboardingStatus>;
    launchReadiness$!: Observable<LaunchReadinessReport>;
    lowStock$!: Observable<LowStockReport>;
    salesSummary$!: Observable<SalesOrderSummary | null>;
    creatingDemoWorkspace = false;
    cleaningDemoData = false;

    constructor(
        private statsService: DashboardStatsService,
        private onboardingService: OnboardingService,
        private lowStockService: LowStockService,
        private salesOrdersService: SalesOrdersService,
        private snackBar: MatSnackBar,
        private dialog: MatDialog,
    ) { }

    ngOnInit(): void {
        this.refresh();
    }

    refresh(): void {
        this.stats$ = this.statsService.getStats();
        this.onboardingStatus$ = this.onboardingService.getStatus();
        this.launchReadiness$ = this.onboardingService.getLaunchReadiness();
        this.lowStock$ = this.lowStockService.getLowStock();
        this.salesSummary$ = this.salesOrdersService.summary(30).pipe(catchError(() => of(null)));
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

    cleanupDemoData(section: LaunchReadinessSection): void {
        if (this.cleaningDemoData || !section.cleanup_available) return;

        const dialogRef = this.dialog.open(ConfirmationDialog, {
            width: '420px',
            data: {
                title: 'Clean up demo data',
                message: 'This removes only records that still match Fulcrum demo fingerprints. Cleanup is blocked automatically if customer activity is detected.'
            } as ConfirmationDialogData
        });

        dialogRef.afterClosed().subscribe((confirmed) => {
            if (!confirmed) return;

            this.cleaningDemoData = true;
            this.onboardingService.cleanupDemoData()
                .pipe(finalize(() => this.cleaningDemoData = false))
                .subscribe({
                    next: (result) => {
                        this.snackBar.open(result.message, 'Close', { duration: 5000 });
                        this.refresh();
                    },
                    error: () => {
                        // HttpErrorInterceptor surfaces the localized backend message
                        // (apiErrors.onboarding.cleanupBlocked / cleanupNotConfirmed).
                        // The nested error.error.detail.blocked_reasons/records can be
                        // read here if we ever want to render the list inline.
                        this.refresh();
                    }
                });
        });
    }

    readinessIcon(section: LaunchReadinessSection): string {
        if (section.status === 'ready') return 'check_circle';
        if (section.status === 'needs_attention') return 'warning';
        if (section.status === 'optional') return 'radio_button_unchecked';
        return 'error';
    }

    demoDataSection(report: LaunchReadinessReport): LaunchReadinessSection | undefined {
        return report.sections.find(section => section.key === 'demo_data');
    }
}
