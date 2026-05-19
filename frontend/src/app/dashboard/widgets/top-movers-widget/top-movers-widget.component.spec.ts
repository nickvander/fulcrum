import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { TopMoversWidgetComponent } from './top-movers-widget.component';
import {
  AnalyticsReportsService,
  TopMoverRow,
  TopMoversResponse,
} from '../../services/analytics-reports.service';

function moverRow(overrides: Partial<TopMoverRow> = {}): TopMoverRow {
  return {
    product_id: 1, name: 'Widget A', sku: 'WID-A',
    units: 3, revenue_amount: 300, cogs_amount: 60,
    overhead_amount: 20, total_cost_amount: 80,
    net_profit_amount: 220, net_margin_percent: 73.3,
    ...overrides,
  };
}

function resp(rows: TopMoverRow[]): TopMoversResponse {
  return { window_days: 30, limit: 10, rows };
}

describe('TopMoversWidgetComponent', () => {
  let fixture: ComponentFixture<TopMoversWidgetComponent>;
  let component: TopMoversWidgetComponent;
  let analyticsStub: { topMovers: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    analyticsStub = {
      topMovers: vi.fn().mockReturnValue(of(resp([]))),
    };
    await TestBed.configureTestingModule({
      imports: [
        TopMoversWidgetComponent,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [{ provide: AnalyticsReportsService, useValue: analyticsStub }],
    }).compileComponents();
    fixture = TestBed.createComponent(TopMoversWidgetComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('asks for the default window + limit on init', () => {
    expect(analyticsStub.topMovers).toHaveBeenCalledWith(
      component.windowDays, component.limit,
    );
  });

  it('renders empty state when no rows are returned', () => {
    expect(fixture.debugElement.query(By.css('[data-testid="top-movers-empty"]'))).not.toBeNull();
  });

  it('renders one row per product with the right testid', () => {
    analyticsStub.topMovers.mockReturnValue(of(resp([
      moverRow({ product_id: 1 }),
      moverRow({ product_id: 2, name: 'Widget B' }),
    ])));
    component.refresh();
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('[data-testid="top-movers-row-1"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="top-movers-row-2"]'))).not.toBeNull();
  });

  it('marginClass classifies negative margins as `margin-negative`, single-digit margins as `margin-warn`, healthy ones plain', () => {
    expect(component.marginClass(moverRow({ net_margin_percent: -5 }))).toBe('margin-negative');
    expect(component.marginClass(moverRow({ net_margin_percent: 5 }))).toBe('margin-warn');
    expect(component.marginClass(moverRow({ net_margin_percent: 50 }))).toBe('');
    expect(component.marginClass(moverRow({ net_margin_percent: null }))).toBe('');
  });

  it('applies the margin class to the margin cell via the testid', () => {
    analyticsStub.topMovers.mockReturnValue(of(resp([
      moverRow({ product_id: 7, net_margin_percent: -10 }),
    ])));
    component.refresh();
    fixture.detectChanges();
    const cell = fixture.debugElement.query(By.css('[data-testid="top-movers-margin-7"]'));
    expect(cell.nativeElement.classList.contains('margin-negative')).toBe(true);
  });

  it('formats currency with no decimals and MXN code', () => {
    expect(component.formatCurrency(199.99)).toContain('MX$');
    expect(component.formatCurrency(199.99)).not.toContain('.99');
  });

  it('formatMargin returns em-dash for null', () => {
    expect(component.formatMargin(null)).toBe('—');
    expect(component.formatMargin(42.789)).toBe('42.8%');
  });

  it('error state renders the error label, no crash', () => {
    fixture.destroy();
    analyticsStub.topMovers.mockReturnValue(throwError(() => new Error('boom')));
    fixture = TestBed.createComponent(TopMoversWidgetComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('[data-testid="top-movers-error"]'))).not.toBeNull();
  });
});
