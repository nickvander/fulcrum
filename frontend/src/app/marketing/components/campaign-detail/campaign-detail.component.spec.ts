
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CampaignDetailComponent } from './campaign-detail.component';
import { MarketingService } from '../../services/marketing.service';
import { ProductService } from '../../../products/services/product';
import { MatDialog } from '@angular/material/dialog';
import { ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('CampaignDetailComponent', () => {
    let component: CampaignDetailComponent;
    let fixture: ComponentFixture<CampaignDetailComponent>;
    let marketingServiceMock: any;
    let productServiceMock: any;
    let dialogMock: any;

    beforeEach(async () => {
        marketingServiceMock = {
            getCampaign: vi.fn().mockReturnValue(of({
                id: 1,
                name: 'Test Campaign',
                events: [],
                status: 'draft',
                budget: 1000,
                spent: 0
            }))
        };

        productServiceMock = {
            getProductById: vi.fn().mockReturnValue(of({ id: 1, name: 'Test Product' }))
        };

        dialogMock = {
            open: vi.fn()
        };

        await TestBed.configureTestingModule({
            imports: [
                CampaignDetailComponent,
                NoopAnimationsModule
            ],
            providers: [
                { provide: MarketingService, useValue: marketingServiceMock },
                { provide: ProductService, useValue: productServiceMock },
                { provide: MatDialog, useValue: dialogMock },
                {
                    provide: ActivatedRoute,
                    useValue: {
                        snapshot: { paramMap: { get: () => '1' } }
                    }
                }
            ]
        }).compileComponents();

        // Explicitly override the provider to ensure the mock is used
        TestBed.overrideProvider(MatDialog, { useValue: dialogMock });

        fixture = TestBed.createComponent(CampaignDetailComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should load campaign on init', () => {
        expect(marketingServiceMock.getCampaign).toHaveBeenCalledWith(1);
        expect(component.campaign).toBeTruthy();
        expect(component.campaign?.name).toBe('Test Campaign');
    });

    it('should open product dialog', () => {
        const productSummary = { id: 1, name: 'Prod', sku: 'SKU', image_url: '' };
        component.openProductDialog(productSummary);
        expect(productServiceMock.getProductById).toHaveBeenCalledWith(1);
        expect(dialogMock.open).toHaveBeenCalled();
    });
});
