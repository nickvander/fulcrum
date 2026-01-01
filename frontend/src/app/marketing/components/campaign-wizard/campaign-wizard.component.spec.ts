
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CampaignWizardComponent } from './campaign-wizard.component';
import { MarketingService } from '../../services/marketing.service';
import { ProductService } from '../../../products/services/product';
import { Router, ActivatedRoute } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { HttpClientTestingModule } from '@angular/common/http/testing';

describe('CampaignWizardComponent', () => {
    let component: CampaignWizardComponent;
    let fixture: ComponentFixture<CampaignWizardComponent>;
    let marketingServiceMock: any;
    let productServiceMock: any;
    let routerMock: any;
    let snackBarMock: any;
    let activatedRouteMock: any;

    beforeEach(async () => {
        marketingServiceMock = {
            getConnectors: vi.fn().mockReturnValue(of([])),
            getCampaign: vi.fn(),
            createCampaign: vi.fn(),
            updateCampaign: vi.fn()
        };

        productServiceMock = {
            searchProducts: vi.fn().mockReturnValue(of({ data: [] }))
        };

        routerMock = {
            navigate: vi.fn()
        };

        snackBarMock = {
            open: vi.fn().mockReturnValue({ onAction: () => of(true) })
        };

        activatedRouteMock = {
            snapshot: {
                paramMap: {
                    get: vi.fn().mockReturnValue(null) // Default to create mode
                }
            }
        };

        await TestBed.configureTestingModule({
            imports: [
                CampaignWizardComponent,
                NoopAnimationsModule,
                HttpClientTestingModule
            ],
            providers: [
                { provide: MarketingService, useValue: marketingServiceMock },
                { provide: ProductService, useValue: productServiceMock },
                { provide: Router, useValue: routerMock },
                { provide: MatSnackBar, useValue: snackBarMock },
                { provide: ActivatedRoute, useValue: activatedRouteMock }
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(CampaignWizardComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should initialize form with default values', () => {
        expect(component.campaignForm).toBeDefined();
        expect(component.campaignForm.get('name')?.value).toBe('');
    });

    it('should load connectors on init', () => {
        expect(marketingServiceMock.getConnectors).toHaveBeenCalled();
    });

    it('should toggle channel selection', () => {
        component.toggleChannel('email');
        expect(component.selectedChannels).toContain('email');
        component.toggleChannel('email');
        expect(component.selectedChannels).not.toContain('email');
    });

    it('should add event', () => {
        const initialCount = component.events.length;
        component.addEvent();
        expect(component.events.length).toBe(initialCount + 1);
    });

    it('should remove event', () => {
        component.addEvent();
        const initialCount = component.events.length;
        component.removeEvent(0);
        expect(component.events.length).toBe(initialCount - 1);
    });
});
