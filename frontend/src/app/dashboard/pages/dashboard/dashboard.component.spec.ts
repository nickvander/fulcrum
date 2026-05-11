import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { DashboardComponent } from './dashboard.component';
import { DashboardStatsService } from '../../services/dashboard-stats.service';
import { OnboardingService } from '../../services/onboarding.service';
import { of } from 'rxjs';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
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
            }))
        };

        await TestBed.configureTestingModule({
            imports: [
                DashboardComponent, // Standalone
                HttpClientTestingModule,
                MatButtonModule,
                MatIconModule,
                MatTooltipModule,
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
                { provide: OnboardingService, useValue: onboardingServiceMock }
            ],
            schemas: [CUSTOM_ELEMENTS_SCHEMA]
        })
            .compileComponents();

        fixture = TestBed.createComponent(DashboardComponent);
        component = fixture.componentInstance;
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
    });
});
