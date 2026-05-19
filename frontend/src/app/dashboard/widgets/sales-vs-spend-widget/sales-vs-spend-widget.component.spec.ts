import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { SalesVsSpendWidgetComponent } from './sales-vs-spend-widget.component';
import {
  AnalyticsReportsService,
  CostRollupDailyResponse,
  CostRollupDailyRow,
} from '../../services/analytics-reports.service';

function day(overrides: Partial<CostRollupDailyRow> = {}): CostRollupDailyRow {
  return {
    date: '2026-05-01', orders: 0,
    revenue_amount_mxn: 0, total_cost_amount: 0, net_profit_amount: 0,
    ...overrides,
  };
}

function series(rows: CostRollupDailyRow[]): CostRollupDailyResponse {
  return { window_days: rows.length, series: rows };
}

describe('SalesVsSpendWidgetComponent', () => {
  let fixture: ComponentFixture<SalesVsSpendWidgetComponent>;
  let component: SalesVsSpendWidgetComponent;
  let analyticsStub: { costRollupDaily: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    analyticsStub = {
      costRollupDaily: vi.fn().mockReturnValue(of(series([]))),
    };
    await TestBed.configureTestingModule({
      imports: [
        SalesVsSpendWidgetComponent,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [{ provide: AnalyticsReportsService, useValue: analyticsStub }],
    }).compileComponents();
    fixture = TestBed.createComponent(SalesVsSpendWidgetComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('asks for the configured window on init', () => {
    expect(analyticsStub.costRollupDaily).toHaveBeenCalledWith(component.windowDays);
  });

  it('treats zero-everywhere series as empty (no chart) so the dashboard does not show a flat line at zero', () => {
    analyticsStub.costRollupDaily.mockReturnValue(of(series([
      day({ date: '2026-05-01' }),
      day({ date: '2026-05-02' }),
    ])));
    component.refresh();
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('[data-testid="sales-vs-spend-empty"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="sales-vs-spend-svg"]'))).toBeNull();
  });

  it('renders the SVG once at least one row has non-zero values', () => {
    analyticsStub.costRollupDaily.mockReturnValue(of(series([
      day({ date: '2026-05-01', revenue_amount_mxn: 0, total_cost_amount: 0 }),
      day({ date: '2026-05-02', revenue_amount_mxn: 100, total_cost_amount: 60, net_profit_amount: 40, orders: 1 }),
    ])));
    component.refresh();
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('[data-testid="sales-vs-spend-svg"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="line-revenue"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="line-cost"]'))).not.toBeNull();
  });

  it('maxValue takes the larger of revenue or cost across the series', () => {
    component.data = series([
      day({ revenue_amount_mxn: 50, total_cost_amount: 200 }),
      day({ revenue_amount_mxn: 300, total_cost_amount: 100 }),
    ]);
    expect(component.maxValue).toBe(300);
  });

  it('maxValue floors at 1 to avoid divide-by-zero scaling', () => {
    component.data = series([day({ date: '2026-05-01' })]);
    expect(component.maxValue).toBe(1);
  });

  it('yFor() maps maxValue to the top of the canvas and 0 to the bottom', () => {
    component.data = series([
      day({ revenue_amount_mxn: 100 }),
      day({ revenue_amount_mxn: 0 }),
    ]);
    // max = 100 → top edge (padding)
    expect(component.yFor(100)).toBeCloseTo(component.PADDING_Y, 4);
    // 0 → bottom edge (height - padding)
    expect(component.yFor(0)).toBeCloseTo(
      component.CANVAS_HEIGHT - component.PADDING_Y, 4,
    );
  });

  it('polyline() returns comma-separated x,y pairs joined by spaces, in input order', () => {
    component.data = series([
      day({ date: '2026-05-01', revenue_amount_mxn: 100 }),
      day({ date: '2026-05-02', revenue_amount_mxn: 50 }),
    ]);
    const points = component.polyline('revenue');
    const parts = points.split(' ');
    expect(parts.length).toBe(2);
    // Each entry is "x,y" — sanity-check shape.
    parts.forEach(p => expect(p.split(',').length).toBe(2));
  });

  it('totals() sums every series row + tags negative profit with the negative class', () => {
    analyticsStub.costRollupDaily.mockReturnValue(of(series([
      day({ revenue_amount_mxn: 100, total_cost_amount: 30, net_profit_amount: 70, orders: 1 }),
      day({ revenue_amount_mxn: 50, total_cost_amount: 200, net_profit_amount: -150, orders: 1 }),
    ])));
    component.refresh();
    fixture.detectChanges();
    const totals = component.totals();
    expect(totals.revenue).toBe(150);
    expect(totals.cost).toBe(230);
    expect(totals.profit).toBe(-80);
    expect(totals.orders).toBe(2);
  });

  it('axisLabels() returns the first and last dates short-formatted', () => {
    component.data = series([
      day({ date: '2026-05-01' }),
      day({ date: '2026-05-30' }),
    ]);
    expect(component.axisLabels()).toEqual({ left: '5/1', right: '5/30' });
  });

  it('error state renders the error label, no crash', () => {
    fixture.destroy();
    analyticsStub.costRollupDaily.mockReturnValue(throwError(() => new Error('boom')));
    fixture = TestBed.createComponent(SalesVsSpendWidgetComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('[data-testid="sales-vs-spend-error"]'))).not.toBeNull();
  });
});
