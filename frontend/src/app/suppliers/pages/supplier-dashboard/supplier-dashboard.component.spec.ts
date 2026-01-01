
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SupplierDashboardComponent } from './supplier-dashboard.component';
import { SuppliersService } from '../../suppliers.service';
import { ScreenService } from '../../../core/services/screen.service';
import { of } from 'rxjs';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';

describe('SupplierDashboardComponent', () => {
    let component: SupplierDashboardComponent;
    let fixture: ComponentFixture<SupplierDashboardComponent>;
    let suppliersServiceMock: any;
    let screenServiceMock: any;

    const mockStats = {
        suppliers: [],
        pos: []
    };

    beforeEach(async () => {
        suppliersServiceMock = {
            getSuppliers: vi.fn().mockReturnValue(of([])),
            getPurchaseOrders: vi.fn().mockReturnValue(of([]))
        };

        screenServiceMock = {
            isMobile$: of(false)
        };

        await TestBed.configureTestingModule({
            imports: [SupplierDashboardComponent, NoopAnimationsModule],
            providers: [
                { provide: SuppliersService, useValue: suppliersServiceMock },
                { provide: ScreenService, useValue: screenServiceMock },
                provideRouter([])
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(SupplierDashboardComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
