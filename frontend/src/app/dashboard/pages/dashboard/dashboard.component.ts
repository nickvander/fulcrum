import { Component, OnInit } from '@angular/core';
import { DashboardStats, DashboardStatsService } from '../../services/dashboard-stats.service';
import { LowStockReport, LowStockRow, LowStockService } from '../../services/low-stock.service';
import { finalize, map, Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { SalesOrderSummary, SalesOrdersService } from '../../../sales-orders/services/sales-orders.service';
import { LaunchReadinessReport, LaunchReadinessSection, OnboardingService, OnboardingStatus } from '../../services/onboarding.service';
import { AnalyticsReportsService, QuestionsListResponse } from '../../services/analytics-reports.service';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MetricCardComponent } from '../../../shared/components/metric-card/metric-card.component';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { LowStockListWidgetComponent } from '../../widgets/low-stock-list/low-stock-list.component';
import { InventoryHealthWidgetComponent } from '../../widgets/inventory-health-widget/inventory-health-widget.component';
import { OnboardingChecklistComponent } from '../../widgets/onboarding-checklist/onboarding-checklist.component';
import { SalesByChannelWidgetComponent } from '../../widgets/sales-by-channel-widget/sales-by-channel-widget.component';
import { AnalyticsReportsWidgetComponent } from '../../widgets/analytics-reports-widget/analytics-reports-widget.component';
import { TodayProfitWidgetComponent } from '../../widgets/today-profit-widget/today-profit-widget.component';
import { SalesVsSpendWidgetComponent } from '../../widgets/sales-vs-spend-widget/sales-vs-spend-widget.component';
import { MarginByChannelWidgetComponent } from '../../widgets/margin-by-channel-widget/margin-by-channel-widget.component';
import { TopMoversWidgetComponent } from '../../widgets/top-movers-widget/top-movers-widget.component';
import { DeadStockWidgetComponent } from '../../widgets/dead-stock-widget/dead-stock-widget.component';
import { RefundsWidgetComponent } from '../../widgets/refunds-widget/refunds-widget.component';
import { ReturnsWidgetComponent } from '../../widgets/returns-widget/returns-widget.component';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterModule } from '@angular/router';
import { TranslocoModule } from '@ngneat/transloco';
import { ConfirmationDialog, ConfirmationDialogData } from '../../../shared/components/confirmation-dialog/confirmation-dialog';

/** Lightweight projection of the buyer-Q&A SLA endpoint for the hero card. */
interface QaSlaSummary {
    breached: number;
    unanswered: number;
    slaHours: number;
}

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
        MetricCardComponent,
        MoneyPipe,
        LowStockListWidgetComponent,
        InventoryHealthWidgetComponent,
        OnboardingChecklistComponent,
        SalesByChannelWidgetComponent,
        AnalyticsReportsWidgetComponent,
        TodayProfitWidgetComponent,
        SalesVsSpendWidgetComponent,
        MarginByChannelWidgetComponent,
        TopMoversWidgetComponent,
        DeadStockWidgetComponent,
        RefundsWidgetComponent,
        ReturnsWidgetComponent,
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
    /** Over-SLA / unanswered buyer-Q&A counts for the hero card. Null while loading or on error. */
    qaSla$!: Observable<QaSlaSummary | null>;
    creatingDemoWorkspace = false;
    cleaningDemoData = false;

    constructor(
        private statsService: DashboardStatsService,
        private onboardingService: OnboardingService,
        private lowStockService: LowStockService,
        private salesOrdersService: SalesOrdersService,
        private analyticsService: AnalyticsReportsService,
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
        this.qaSla$ = this.analyticsService.questionsList(30, 0, 1).pipe(
            map((resp: QuestionsListResponse): QaSlaSummary => ({
                breached: resp.breached_count ?? 0,
                unanswered: resp.unanswered_count ?? 0,
                slaHours: resp.sla_hours ?? 24,
            })),
            catchError(() => of(null)),
        );
    }

    /**
     * Progressive disclosure: a brand-new / empty account shows the
     * primeros-pasos hero + onboarding checklist instead of the wall of
     * zero widgets. "Empty" = required onboarding still incomplete AND no
     * catalog yet (no products). Once the operator has products we show
     * the FULL cockpit (no widget removed — Sofía density guardrail).
     */
    isEmptyAccount(stats: DashboardStats, onboarding: OnboardingStatus | null): boolean {
        const noCatalog = (stats?.totalProducts ?? 0) === 0;
        const onboardingIncomplete = !!onboarding && !onboarding.complete;
        return noCatalog && onboardingIncomplete;
    }

    /** Tone for the QA SLA card: error if any breached, warning if any unanswered, else positive. */
    qaTone(qa: QaSlaSummary | null): 'positive' | 'negative' | 'neutral' {
        if (!qa) return 'neutral';
        if (qa.breached > 0) return 'negative';
        return 'neutral';
    }

    /** Combined critical+low rows for the dense "needs attention" table (cap for the dashboard snapshot). */
    needsAttentionRows(report: LowStockReport | null): LowStockRow[] {
        if (!report?.rows?.length) return [];
        return report.rows
            .filter(r => r.severity === 'critical' || r.severity === 'low')
            .slice(0, 8);
    }

    severityChipClass(severity: LowStockRow['severity']): string {
        if (severity === 'critical') return 'app-chip-error';
        if (severity === 'low') return 'app-chip-warning';
        return 'app-chip-neutral';
    }

    daysLeftLabel(row: LowStockRow): string {
        if (!row.daily_velocity || row.daily_velocity <= 0) return '—';
        if (row.days_of_inventory >= 999) return '—';
        return `${row.days_of_inventory.toFixed(1)}d`;
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
