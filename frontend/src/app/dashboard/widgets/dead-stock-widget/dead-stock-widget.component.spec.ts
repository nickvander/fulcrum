import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { DeadStockWidgetComponent } from './dead-stock-widget.component';
import {
  AnalyticsReportsService,
  DeadStockResponse,
  DeadStockRow,
} from '../../services/analytics-reports.service';

function deadRow(overrides: Partial<DeadStockRow> = {}): DeadStockRow {
  return {
    product_id: 1, product_name: 'Widget Z', product_sku: 'DEAD-Z',
    on_hand: 5, units_sold: 0, daily_velocity: 0,
    days_since_last_sale: 60, cost_price: 10, stock_value_at_cost: 50,
    ...overrides,
  };
}

function resp(rows: DeadStockRow[]): DeadStockResponse {
  return { window_days: 30, threshold_daily_velocity: 0.1, rows };
}

describe('DeadStockWidgetComponent', () => {
  let fixture: ComponentFixture<DeadStockWidgetComponent>;
  let component: DeadStockWidgetComponent;
  let analyticsStub: { deadStock: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    analyticsStub = {
      deadStock: vi.fn().mockReturnValue(of(resp([]))),
    };
    await TestBed.configureTestingModule({
      imports: [
        DeadStockWidgetComponent,
        NoopAnimationsModule,
        RouterTestingModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [{ provide: AnalyticsReportsService, useValue: analyticsStub }],
    }).compileComponents();
    fixture = TestBed.createComponent(DeadStockWidgetComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('calls the dead-stock endpoint with the configured window + threshold + limit', () => {
    expect(analyticsStub.deadStock).toHaveBeenCalledWith(
      component.windowDays, component.thresholdDailyVelocity, component.limit,
    );
  });

  it('renders the empty state when no dead-stock rows come back', () => {
    expect(fixture.debugElement.query(By.css('[data-testid="dead-stock-empty"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="dead-stock-table"]'))).toBeNull();
  });

  it('renders one row per product when the table is non-empty', () => {
    analyticsStub.deadStock.mockReturnValue(of(resp([
      deadRow({ product_id: 1 }),
      deadRow({ product_id: 2, product_sku: 'DEAD-B' }),
    ])));
    component.refresh();
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('[data-testid="dead-stock-row-1"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="dead-stock-row-2"]'))).not.toBeNull();
  });

  it('renders the capital-at-risk tag with the sum of stock values', () => {
    analyticsStub.deadStock.mockReturnValue(of(resp([
      deadRow({ product_id: 1, stock_value_at_cost: 100 }),
      deadRow({ product_id: 2, stock_value_at_cost: 250 }),
    ])));
    component.refresh();
    fixture.detectChanges();
    const tag = fixture.debugElement.query(By.css('[data-testid="dead-stock-at-risk"]'));
    expect(tag).not.toBeNull();
    expect(tag.nativeElement.textContent).toContain('350');
  });

  it('ageClass returns the right severity bucket for the operator', () => {
    expect(component.ageClass(deadRow({ days_since_last_sale: null }))).toBe('age-never');
    expect(component.ageClass(deadRow({ days_since_last_sale: 200 }))).toBe('age-critical');
    expect(component.ageClass(deadRow({ days_since_last_sale: 90 }))).toBe('age-critical');
    expect(component.ageClass(deadRow({ days_since_last_sale: 45 }))).toBe('age-warn');
    expect(component.ageClass(deadRow({ days_since_last_sale: 10 }))).toBe('');
  });

  it('applies the never-sold class to never-sold rows via the testid', () => {
    analyticsStub.deadStock.mockReturnValue(of(resp([
      deadRow({ product_id: 7, days_since_last_sale: null }),
    ])));
    component.refresh();
    fixture.detectChanges();
    const cell = fixture.debugElement.query(By.css('[data-testid="dead-stock-age-7"]'));
    expect(cell.nativeElement.classList.contains('age-never')).toBe(true);
  });

  it('totalAtRisk sums stock_value_at_cost ignoring null values', () => {
    component.data = resp([
      deadRow({ stock_value_at_cost: 100 }),
      deadRow({ stock_value_at_cost: null }),
      deadRow({ stock_value_at_cost: 50 }),
    ]);
    expect(component.totalAtRisk()).toBe(150);
  });

  it('formatCurrency returns em-dash for null', () => {
    expect(component.formatCurrency(null)).toBe('—');
    expect(component.formatCurrency(undefined)).toBe('—');
    expect(component.formatCurrency(1500)).toContain('MX$');
  });

  it('renders the error block on initial-load failure without crashing', () => {
    // The widget keeps stale data on a refresh error (same pattern
    // as the other analytics widgets). For the error visual to
    // render, the error mock must be active when ngOnInit subscribes.
    fixture.destroy();
    analyticsStub.deadStock.mockReturnValue(throwError(() => new Error('boom')));
    fixture = TestBed.createComponent(DeadStockWidgetComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('[data-testid="dead-stock-error"]'))).not.toBeNull();
  });
});
