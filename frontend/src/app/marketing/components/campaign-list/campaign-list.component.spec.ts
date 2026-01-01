
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CampaignListComponent } from './campaign-list.component';
import { MarketingService } from '../../services/marketing.service';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { ActivatedRoute } from '@angular/router';

describe('CampaignListComponent', () => {
    let component: CampaignListComponent;
    let fixture: ComponentFixture<CampaignListComponent>;
    let marketingServiceMock: any;
    let dialogMock: any;
    let snackBarMock: any;

    beforeEach(async () => {
        marketingServiceMock = {
            getCampaigns: vi.fn().mockReturnValue(of([])),
            getQuickPosts: vi.fn().mockReturnValue(of([])),
            deleteCampaign: vi.fn(),
            deleteEvent: vi.fn()
        };

        dialogMock = {
            open: vi.fn().mockReturnValue({
                afterClosed: () => of(true)
            })
        };

        snackBarMock = {
            open: vi.fn()
        };

        await TestBed.configureTestingModule({
            imports: [
                CampaignListComponent,
                NoopAnimationsModule,
                HttpClientTestingModule
            ],
            providers: [
                { provide: MarketingService, useValue: marketingServiceMock },
                { provide: MatDialog, useValue: dialogMock },
                { provide: MatSnackBar, useValue: snackBarMock },
                {
                    provide: ActivatedRoute,
                    useValue: {
                        snapshot: { paramMap: { get: () => null } }
                    }
                }
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(CampaignListComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should load campaigns and quick posts on init', () => {
        expect(marketingServiceMock.getCampaigns).toHaveBeenCalled();
        expect(marketingServiceMock.getQuickPosts).toHaveBeenCalled();
    });

    it('should apply filters', () => {
        component.campaigns = [
            { id: 1, name: 'C1', status: 'active', events: [], budget: 0, spent: 0 },
            { id: 2, name: 'C2', status: 'draft', events: [], budget: 0, spent: 0 }
        ] as any[];

        component.setStatusFilter('active');
        expect(component.filteredCampaigns.data.length).toBe(1);
        expect(component.filteredCampaigns.data[0].status).toBe('active');

        component.setStatusFilter('all');
        expect(component.filteredCampaigns.data.length).toBe(2);
    });
});
