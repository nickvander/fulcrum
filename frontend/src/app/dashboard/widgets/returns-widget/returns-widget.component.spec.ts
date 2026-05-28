import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { ReturnsWidgetComponent } from './returns-widget.component';
import {
  AnalyticsReportsService,
  ReturnsSummaryResponse,
} from '../../services/analytics-reports.service';

function makeSummary(over: Partial<ReturnsSummaryResponse> = {}): ReturnsSummaryResponse {
  return {
    window_label: 'window 30d',
    totals: {
      source: 'ALL',
      returns_count: 0,
      units_returned: 0,
      value_at_cost_mxn: 0,
    },
    by_channel: [],
    ...over,
  } as ReturnsSummaryResponse;
}

describe('ReturnsWidgetComponent', () => {
  let fixture: ComponentFixture<ReturnsWidgetComponent>;
  let component: ReturnsWidgetComponent;
  let analyticsStub: { returnsSummary: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    analyticsStub = {
      returnsSummary: vi.fn().mockReturnValue(of(makeSummary())),
    };

    await TestBed.configureTestingModule({
      imports: [
        ReturnsWidgetComponent,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: AnalyticsReportsService, useValue: analyticsStub },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ReturnsWidgetComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('fetches on init with the 30d window', () => {
    expect(analyticsStub.returnsSummary).toHaveBeenCalledWith(30);
  });

  it('renders empty state when no channel has activity', () => {
    expect(fixture.debugElement.query(By.css('[data-testid="returns-widget-empty"]'))).not.toBeNull();
  });

  it('renders the totals hero with count + units + value-at-cost', () => {
    analyticsStub.returnsSummary.mockReturnValue(of(makeSummary({
      totals: {
        source: 'ALL', returns_count: 5, units_returned: 12, value_at_cost_mxn: 387,
      },
    })));
    component.refresh();
    fixture.detectChanges();
    const hero = fixture.debugElement.query(By.css('[data-testid="returns-widget-hero"]'));
    expect(hero).not.toBeNull();
    expect(hero.nativeElement.textContent).toContain('5');
    expect(hero.nativeElement.textContent).toContain('12');
  });

  it('hides channels with zero returns even if returned in by_channel', () => {
    analyticsStub.returnsSummary.mockReturnValue(of(makeSummary({
      totals: { source: 'ALL', returns_count: 2, units_returned: 4, value_at_cost_mxn: 80 },
      by_channel: [
        { source: 'AMAZON', returns_count: 2, units_returned: 4, value_at_cost_mxn: 80 },
        { source: 'MERCADOLIBRE', returns_count: 0, units_returned: 0, value_at_cost_mxn: 0 },
      ],
    })));
    component.refresh();
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('[data-testid="returns-channel-AMAZON"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="returns-channel-MERCADOLIBRE"]'))).toBeNull();
  });

  it('shows an error state on first-load failure', () => {
    component.summary = null;
    analyticsStub.returnsSummary.mockReturnValue(throwError(() => new Error('500')));
    component.refresh();
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('[data-testid="returns-widget-error"]'))).not.toBeNull();
  });

  it('channelLabel() formats source codes for display', () => {
    expect(component.channelLabel('MERCADOLIBRE')).toBe('MercadoLibre');
    expect(component.channelLabel('AMAZON')).toBe('Amazon');
    expect(component.channelLabel('UNKNOWN')).toBe('Unknown');
    expect(component.channelLabel('OTHER')).toBe('OTHER');
  });
});
