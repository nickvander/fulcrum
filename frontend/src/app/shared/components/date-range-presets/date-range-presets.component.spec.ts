
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { DateRangePresetsComponent } from './date-range-presets.component';
import { DateRangeService } from '../../services/date-range.service';
import { of } from 'rxjs';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('DateRangePresetsComponent', () => {
    let component: DateRangePresetsComponent;
    let fixture: ComponentFixture<DateRangePresetsComponent>;
    let dateRangeServiceMock: any;

    beforeEach(async () => {
        dateRangeServiceMock = {
            dateRange$: of({ preset: 'week', startDate: new Date(), endDate: new Date() }),
            setPreset: vi.fn(),
            setCustomRange: vi.fn(),
            getDateRangeFromPreset: vi.fn().mockReturnValue({ preset: 'week', startDate: new Date(), endDate: new Date() }),
            getRangeDescription: vi.fn().mockReturnValue('Test Range')
        };

        await TestBed.configureTestingModule({
            imports: [DateRangePresetsComponent, NoopAnimationsModule],
            providers: [
                { provide: DateRangeService, useValue: dateRangeServiceMock }
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(DateRangePresetsComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
