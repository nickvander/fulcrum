import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { DashboardComponent } from './dashboard.component';
import { DashboardStatsService } from '../../services/dashboard-stats.service';
import { LowStockService } from '../../services/low-stock.service';
import { OnboardingService } from '../../services/onboarding.service';
import { SalesOrdersService } from '../../../sales-orders/services/sales-orders.service';
import { of } from 'rxjs';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { vi } from 'vitest';

describe('DashboardComponent', () => {
    let component: DashboardComponent;
    let fixture: ComponentFixture<DashboardComponent>;
    let statsServiceMock: any;
    let onboardingServiceMock: any;
    let lowStockServiceMock: any;
    let salesOrdersServiceMock: any;
    let snackBarMock: any;
    let dialogMock: any;

    beforeEach(async () => {
        statsServiceMock = {
            getStats: vi.fn().mockReturnValue(of({
                totalProducts: 100,
                lowStockCount: 5,
                pendingOrdersCount: 3,
                totalSuppliers: 10,
                lowStockProducts: [],
                totalInventoryValue: 50000,
                stockHealthPercentage: 5
            }))
        };
        onboardingServiceMock = {
            getStatus: vi.fn().mockReturnValue(of({
                complete: false,
                completed_required: 1,
                total_required: 2,
                steps: [
                    {
                        key: 'products',
                        label: 'Products',
                        description: 'Add products',
                        complete: false,
                        optional: false,
                        warning: true,
                        action_label: 'Add products',
                        route: '/products',
                        count: 0
                    }
                ]
            })),
            getLaunchReadiness: vi.fn().mockReturnValue(of({
                status: 'blocked',
                ready: false,
                summary: {
                    blocked: 1,
                    needs_attention: 0,
                    ready: 0,
                    optional: 0
                },
                sections: [
                    {
                        key: 'setup',
                        label: 'Setup',
                        status: 'blocked',
                        description: 'Required setup steps still need attention.',
                        action_label: 'Review checklist',
                        route: '/dashboard',
                        metrics: {}
                    },
                    {
                        key: 'demo_data',
                        label: 'Demo data',
                        status: 'ready',
                        description: 'No demo records were detected.',
                        action_label: 'Review records',
                        route: '/dashboard',
                        metrics: { demo_records: 0 },
                        records: [],
                        cleanup_available: false,
                        blocked_reasons: []
                    }
                ]
            })),
            createDemoWorkspace: vi.fn().mockReturnValue(of({
                created: true,
                created_resources: ['product'],
                supplier_id: 1,
                product_id: 2,
                purchase_order_id: 3,
                message: 'Demo workspace created.'
            })),
            cleanupDemoData: vi.fn().mockReturnValue(of({
                cleaned: true,
                has_demo_data: false,
                cleanup_available: false,
                blocked_reasons: [],
                records: [],
                removed_records: ['product and demo inventory'],
                message: 'Demo data cleaned up by admin@example.com.'
            }))
        };
        lowStockServiceMock = {
            getLowStock: vi.fn().mockReturnValue(of({
                rows: [],
                total_critical: 0,
                total_low: 0,
                total_watch: 0,
            }))
        };
        dialogMock = {
            open: vi.fn().mockReturnValue({
                afterClosed: vi.fn().mockReturnValue(of(true))
            })
        };
        salesOrdersServiceMock = {
            summary: vi.fn().mockReturnValue(of({
                window_days: 30,
                total_orders: 0,
                total_revenue: 0,
                open_orders: 0,
                by_channel: []
            }))
        };
        snackBarMock = {
            open: vi.fn()
        };

        await TestBed.configureTestingModule({
            imports: [
                DashboardComponent, // Standalone
                HttpClientTestingModule,
                MatButtonModule,
                MatDialogModule,
                MatIconModule,
                MatTooltipModule,
                MatSnackBarModule,
                MatProgressSpinnerModule,
                BrowserAnimationsModule,
                RouterTestingModule,
                TranslocoTestingModule.forRoot({
                    langs: { en: {}, es: {} },
                    translocoConfig: { availableLangs: ['en', 'es'], defaultLang: 'en' }
                })
            ],
            providers: [
                { provide: DashboardStatsService, useValue: statsServiceMock },
                { provide: OnboardingService, useValue: onboardingServiceMock },
                { provide: LowStockService, useValue: lowStockServiceMock },
                { provide: SalesOrdersService, useValue: salesOrdersServiceMock },
                { provide: MatSnackBar, useValue: snackBarMock },
                { provide: MatDialog, useValue: dialogMock }
            ],
            schemas: [CUSTOM_ELEMENTS_SCHEMA]
        })
            .compileComponents();

        fixture = TestBed.createComponent(DashboardComponent);
        component = fixture.componentInstance;
        (component as any).snackBar = snackBarMock;
        (component as any).dialog = dialogMock;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should fetch stats on init', () => {
        expect(statsServiceMock.getStats).toHaveBeenCalled();
    });

    it('should fetch onboarding status on init', () => {
        expect(onboardingServiceMock.getStatus).toHaveBeenCalled();
        expect(onboardingServiceMock.getLaunchReadiness).toHaveBeenCalled();
    });

    it('should create a demo workspace and refresh dashboard data', async () => {
        onboardingServiceMock.getStatus.mockClear();
        statsServiceMock.getStats.mockClear();

        component.createDemoWorkspace();
        await fixture.whenStable();

        expect(onboardingServiceMock.createDemoWorkspace).toHaveBeenCalled();
        expect(snackBarMock.open).toHaveBeenCalledWith('Demo workspace created.', 'Close', { duration: 5000 });
        expect(statsServiceMock.getStats).toHaveBeenCalled();
        expect(onboardingServiceMock.getStatus).toHaveBeenCalled();
    });

    it('should render demo records in the launch readiness guardrail', async () => {
        component.launchReadiness$ = of({
            status: 'needs_attention',
            ready: false,
            summary: {
                blocked: 0,
                needs_attention: 1,
                ready: 3,
                optional: 1
            },
            sections: [
                {
                    key: 'demo_data',
                    label: 'Demo data',
                    status: 'needs_attention',
                    description: 'Demo records exist.',
                    action_label: 'Review records',
                    route: '/dashboard',
                    metrics: { demo_records: 1 },
                    cleanup_available: true,
                    blocked_reasons: [],
                    records: [
                        {
                            key: 'product:2',
                            type: 'Product',
                            id: 2,
                            label: '[Demo] Starter Widget',
                            identifier: 'DEMO-STARTER-WIDGET',
                            description: 'Seed product used for supplier matching.',
                            route: '/products',
                            safe_to_delete: true,
                            blockers: []
                        }
                    ]
                }
            ]
        });

        fixture.detectChanges();
        await fixture.whenStable();

        const text = fixture.nativeElement.textContent;
        expect(text).toContain('Review before go-live');
        expect(text).toContain('[Demo] Starter Widget');
        expect(text).toContain('DEMO-STARTER-WIDGET');
    });

    it('should confirm and clean up demo data', async () => {
        onboardingServiceMock.getStatus.mockClear();
        statsServiceMock.getStats.mockClear();

        component.cleanupDemoData({
            key: 'demo_data',
            label: 'Demo data',
            status: 'needs_attention',
            description: 'Demo records exist.',
            action_label: 'Review records',
            route: '/dashboard',
            metrics: { demo_records: 1 },
            cleanup_available: true,
            blocked_reasons: [],
            records: []
        });
        await fixture.whenStable();

        expect(dialogMock.open).toHaveBeenCalled();
        expect(onboardingServiceMock.cleanupDemoData).toHaveBeenCalled();
        expect(snackBarMock.open).toHaveBeenCalledWith(
            'Demo data cleaned up by admin@example.com.',
            'Close',
            { duration: 5000 }
        );
        expect(statsServiceMock.getStats).toHaveBeenCalled();
        expect(onboardingServiceMock.getStatus).toHaveBeenCalled();
    });
});
