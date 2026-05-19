import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { TodayProfitWidgetComponent } from './today-profit-widget.component';
import { AnalyticsReportsService, CostRollup } from '../../services/analytics-reports.service';

function rollup(overrides: Partial<CostRollup> = {}): CostRollup {
  return {
    window_days: 1,
    source: null,
    orders: 0,
    revenue_amount_mxn: 0,
    cogs_amount: 0,
    marketplace_fees_amount: 0,
    shipping_cost_amount: 0,
    ad_spend_amount: 0,
    other_cost_amount: 0,
    total_cost_amount: 0,
    net_profit_amount: 0,
    net_margin_percent: null,
    ...overrides,
  };
}

describe('TodayProfitWidgetComponent', () => {
  let fixture: ComponentFixture<TodayProfitWidgetComponent>;
  let component: TodayProfitWidgetComponent;
  let analyticsStub: { costRollup: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    analyticsStub = {
      costRollup: vi.fn().mockReturnValue(of(rollup())),
    };
    await TestBed.configureTestingModule({
      imports: [
        TodayProfitWidgetComponent,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [{ provide: AnalyticsReportsService, useValue: analyticsStub }],
    }).compileComponents();
    fixture = TestBed.createComponent(TodayProfitWidgetComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('asks for a 24h window on init', () => {
    expect(analyticsStub.costRollup).toHaveBeenCalledWith(1);
  });

  it('renders the empty state when there are no orders today', () => {
    expect(fixture.debugElement.query(By.css('[data-testid="today-profit-empty"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="today-profit-hero"]'))).toBeNull();
  });

  it('renders the hero block when orders exist + uses positive class for a profitable day', () => {
    analyticsStub.costRollup.mockReturnValue(of(rollup({
      orders: 5, revenue_amount_mxn: 1000, total_cost_amount: 600,
      net_profit_amount: 400, net_margin_percent: 40,
    })));
    component.refresh();
    fixture.detectChanges();

    const hero = fixture.debugElement.query(By.css('[data-testid="today-profit-hero"]'));
    expect(hero).not.toBeNull();
    expect(hero.nativeElement.classList.contains('profit-positive')).toBe(true);
  });

  it('uses the negative class when net profit is below zero (loss-making day)', () => {
    analyticsStub.costRollup.mockReturnValue(of(rollup({
      orders: 2, revenue_amount_mxn: 100, total_cost_amount: 150,
      net_profit_amount: -50, net_margin_percent: -50,
    })));
    component.refresh();
    fixture.detectChanges();

    const hero = fixture.debugElement.query(By.css('[data-testid="today-profit-hero"]'));
    expect(hero.nativeElement.classList.contains('profit-negative')).toBe(true);
  });

  it('formats currency with no decimals and MXN code', () => {
    expect(component.formatCurrency(1234.56)).toContain('MX$');
    expect(component.formatCurrency(1234.56)).not.toContain('.5');
    expect(component.formatCurrency(null)).toBe('—');
  });

  it('formats margin as a 1-decimal percent and renders an em-dash for null', () => {
    expect(component.formatMargin(42.789)).toBe('42.8%');
    expect(component.formatMargin(null)).toBe('—');
  });

  it('on error, shows the error state without crashing', () => {
    // The widget only renders the error block when there's no rollup
    // data yet (otherwise we'd rather show stale data than blank the
    // headline). So tear down + recreate the fixture with the
    // error-returning mock active from the very first call.
    fixture.destroy();
    analyticsStub.costRollup.mockReturnValue(throwError(() => new Error('boom')));
    fixture = TestBed.createComponent(TodayProfitWidgetComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('[data-testid="today-profit-error"]'))).not.toBeNull();
  });
});
