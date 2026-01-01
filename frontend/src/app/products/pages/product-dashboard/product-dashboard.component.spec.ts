
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ProductDashboardComponent } from './product-dashboard.component';
import { DashboardStatsService, DashboardStats } from '../../../dashboard/services/dashboard-stats.service';
import { ScreenService } from '../../../core/services/screen.service';
import { of } from 'rxjs';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';

describe('ProductDashboardComponent', () => {
    let component: ProductDashboardComponent;
    let fixture: ComponentFixture<ProductDashboardComponent>;
    let statsServiceMock: any;
    let screenServiceMock: any;

    const mockStats: DashboardStats = {
        totalProducts: 10,
        totalInventoryValue: 1000,
        lowStockCount: 2,
        stockHealthPercentage: 90,
        lowStockProducts: []
    } as any;

    beforeEach(async () => {
        statsServiceMock = {
            getStats: vi.fn().mockReturnValue(of(mockStats))
        };

        screenServiceMock = {
            isMobile$: of(false)
        };

        await TestBed.configureTestingModule({
            imports: [ProductDashboardComponent, NoopAnimationsModule],
            providers: [
                { provide: DashboardStatsService, useValue: statsServiceMock },
                { provide: ScreenService, useValue: screenServiceMock },
                provideRouter([])
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(ProductDashboardComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should load stats on init', () => {
        component.stats$.subscribe(stats => {
            expect(stats).toEqual(mockStats);
        });
        expect(statsServiceMock.getStats).toHaveBeenCalled();
    });
});
