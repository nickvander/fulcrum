import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { of, throwError } from 'rxjs';

import { getTranslocoTestingModule } from '../../../testing/transloco-testing';
import { ProfitSummaryWidgetComponent } from './profit-summary-widget.component';
import {
  AnalyticsReportsService,
  ProfitSummary,
} from '../../services/analytics-reports.service';

function summary(overrides: Partial<ProfitSummary> = {}): ProfitSummary {
  return {
    period: 'this_month',
    start: '2026-05-01',
    end: '2026-05-31',
    window_days: 31,
    revenue_amount_mxn: 0,
    sales_costs_amount: 0,
    contribution_profit_amount: 0,
    operating_expenses_amount: 0,
    bottom_line_amount: 0,
    net_margin_percent: null,
    orders: 0,
    has_realized_orders: false,
    verdict: null,
    double_count_warning: true,
    excluded_categories: [],
    ...overrides,
  };
}

const WON = summary({
  revenue_amount_mxn: 500,
  sales_costs_amount: 100,
  contribution_profit_amount: 400,
  operating_expenses_amount: 150,
  bottom_line_amount: 250,
  orders: 3,
  has_realized_orders: true,
  verdict: 'won',
});

const LOST = summary({
  revenue_amount_mxn: 500,
  sales_costs_amount: 100,
  contribution_profit_amount: 400,
  operating_expenses_amount: 600,
  bottom_line_amount: -200,
  orders: 3,
  has_realized_orders: true,
  verdict: 'lost',
});

describe('ProfitSummaryWidgetComponent', () => {
  let fixture: ComponentFixture<ProfitSummaryWidgetComponent>;
  let component: ProfitSummaryWidgetComponent;
  let analyticsStub: { profitSummary: ReturnType<typeof vi.fn> };

  async function setup(initial: ProfitSummary = summary()) {
    analyticsStub = {
      profitSummary: vi.fn().mockReturnValue(of(initial)),
    };
    await TestBed.configureTestingModule({
      imports: [
        ProfitSummaryWidgetComponent,
        NoopAnimationsModule,
        RouterTestingModule,
        getTranslocoTestingModule(),
      ],
      providers: [{ provide: AnalyticsReportsService, useValue: analyticsStub }],
    }).compileComponents();
    fixture = TestBed.createComponent(ProfitSummaryWidgetComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  it('fetches this_month on init by default', async () => {
    await setup();
    expect(analyticsStub.profitSummary).toHaveBeenCalledWith('this_month');
  });

  it('shows the empty state (no fake $0) when there are no realized orders', async () => {
    await setup(summary({ has_realized_orders: false, verdict: null }));
    expect(fixture.debugElement.query(By.css('[data-testid="profit-empty"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="profit-hero"]'))).toBeNull();
  });

  it('renders a profit with the success token + up arrow', async () => {
    await setup(WON);
    const hero = fixture.debugElement.query(By.css('[data-testid="profit-hero"]'));
    expect(hero).not.toBeNull();
    expect(hero.nativeElement.classList.contains('result-won')).toBe(true);
    const icon = fixture.debugElement.query(By.css('[data-testid="profit-verdict-icon"]'));
    expect(icon.nativeElement.textContent.trim()).toBe('arrow_upward');
  });

  it('renders a loss with the danger token + down arrow (never chile-red)', async () => {
    await setup(LOST);
    const hero = fixture.debugElement.query(By.css('[data-testid="profit-hero"]'));
    expect(hero.nativeElement.classList.contains('result-lost')).toBe(true);
    const icon = fixture.debugElement.query(By.css('[data-testid="profit-verdict-icon"]'));
    expect(icon.nativeElement.textContent.trim()).toBe('arrow_downward');
    // The big number must NOT carry the primary/chile-red class.
    expect(hero.nativeElement.classList.contains('result-won')).toBe(false);
  });

  it('shows the big honest MXN number with code', async () => {
    await setup(WON);
    const hero = fixture.debugElement.query(By.css('[data-testid="profit-hero"]'));
    const txt = hero.nativeElement.textContent;
    expect(txt).toContain('MX$');
    expect(txt).toContain('MXN');
    expect(txt).toContain('250');
  });

  it('renders the breakdown ladder values', async () => {
    await setup(WON);
    const ladder = fixture.debugElement.query(By.css('[data-testid="profit-ladder"]'));
    const txt = ladder.nativeElement.textContent;
    expect(txt).toContain('500'); // revenue
    expect(txt).toContain('100'); // sales costs
    expect(txt).toContain('400'); // contribution
    expect(txt).toContain('150'); // operating expenses
  });

  it('switches period and refetches', async () => {
    await setup(WON);
    component.selectPeriod('last_7d');
    expect(component.period).toBe('last_7d');
    expect(analyticsStub.profitSummary).toHaveBeenLastCalledWith('last_7d');
  });

  it('does not refetch when the same period is reselected', async () => {
    await setup(WON);
    analyticsStub.profitSummary.mockClear();
    component.selectPeriod('this_month');
    expect(analyticsStub.profitSummary).not.toHaveBeenCalled();
  });

  it('shows the double-count footnote when flagged', async () => {
    await setup(WON);
    expect(fixture.debugElement.query(By.css('[data-testid="profit-footnote"]'))).not.toBeNull();
  });

  it('shows a "Ver detalle" link only in compact mode', async () => {
    await setup(WON);
    component.compact = true;
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('[data-testid="profit-detail-link"]'))).not.toBeNull();
  });

  it('shows the error state without crashing', async () => {
    analyticsStub = {
      profitSummary: vi.fn().mockReturnValue(throwError(() => new Error('boom'))),
    };
    await TestBed.configureTestingModule({
      imports: [
        ProfitSummaryWidgetComponent,
        NoopAnimationsModule,
        RouterTestingModule,
        getTranslocoTestingModule(),
      ],
      providers: [{ provide: AnalyticsReportsService, useValue: analyticsStub }],
    }).compileComponents();
    fixture = TestBed.createComponent(ProfitSummaryWidgetComponent);
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('[data-testid="profit-error"]'))).not.toBeNull();
  });
});
