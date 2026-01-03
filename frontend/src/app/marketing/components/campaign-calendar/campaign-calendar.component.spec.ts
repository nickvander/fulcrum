
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CampaignCalendarComponent } from './campaign-calendar.component';
import { MarketingService } from '../../services/marketing.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';
import { TranslocoTestingModule } from '@ngneat/transloco';

describe('CampaignCalendarComponent', () => {
    let component: CampaignCalendarComponent;
    let fixture: ComponentFixture<CampaignCalendarComponent>;
    let marketingServiceMock: any;
    let snackBarMock: any;

    beforeEach(async () => {
        marketingServiceMock = {
            getEvents: vi.fn().mockReturnValue(of([])),
            updateEvent: vi.fn()
        };

        snackBarMock = {
            open: vi.fn()
        };

        await TestBed.configureTestingModule({
            imports: [
                CampaignCalendarComponent,
                NoopAnimationsModule,
                HttpClientTestingModule,
                TranslocoTestingModule.forRoot({ langs: { en: {}, 'es-MX': {} } })
            ],
            providers: [
                { provide: MarketingService, useValue: marketingServiceMock },
                { provide: MatSnackBar, useValue: snackBarMock },
                {
                    provide: ActivatedRoute,
                    useValue: {
                        snapshot: { paramMap: { get: () => null } }
                    }
                }
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(CampaignCalendarComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should load events on init', () => {
        expect(marketingServiceMock.getEvents).toHaveBeenCalled();
    });

    it('should navigate months', () => {
        const initialMonth = component.currentDate.getMonth();
        component.nextMonth();
        expect(component.currentDate.getMonth()).not.toBe(initialMonth);
        component.previousMonth();
        expect(component.currentDate.getMonth()).toBe(initialMonth);
    });

    it('should generate calendar grid', () => {
        component.generateCalendar();
        expect(component.calendarDays.length).toBeGreaterThan(0);
    });
});
