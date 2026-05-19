import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { RefundsWidgetComponent } from './refunds-widget.component';
import {
  AnalyticsReportsService,
  RefundsSummaryResponse,
} from '../../services/analytics-reports.service';

function makeSummary(over: Partial<RefundsSummaryResponse> = {}): RefundsSummaryResponse {
  return {
    window_label: 'window 30d',
    totals: {
      source: 'ALL',
      refunds_count: 0,
      refunded_amount_mxn: 0,
      realized_orders_count: 0,
      refund_rate_percent: null,
    },
    by_channel: [
      { source: 'FULCRUM', refunds_count: 0, refunded_amount_mxn: 0, realized_orders_count: 0, refund_rate_percent: null },
      { source: 'MERCADOLIBRE', refunds_count: 0, refunded_amount_mxn: 0, realized_orders_count: 0, refund_rate_percent: null },
      { source: 'AMAZON', refunds_count: 0, refunded_amount_mxn: 0, realized_orders_count: 0, refund_rate_percent: null },
    ],
    ...over,
  } as RefundsSummaryResponse;
}

describe('RefundsWidgetComponent', () => {
  let fixture: ComponentFixture<RefundsWidgetComponent>;
  let component: RefundsWidgetComponent;
  let analyticsStub: { refundsSummary: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    analyticsStub = {
      refundsSummary: vi.fn().mockReturnValue(of(makeSummary())),
    };

    await TestBed.configureTestingModule({
      imports: [
        RefundsWidgetComponent,
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

    fixture = TestBed.createComponent(RefundsWidgetComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('fetches on init with the 30d window', () => {
    expect(analyticsStub.refundsSummary).toHaveBeenCalledWith(30);
  });

  it('renders the totals + empty state when no channel has activity', () => {
    const hero = fixture.debugElement.query(By.css('[data-testid="refunds-widget-hero"]'));
    expect(hero).not.toBeNull();
    const empty = fixture.debugElement.query(By.css('[data-testid="refunds-widget-empty"]'));
    expect(empty).not.toBeNull();
  });

  it('renders one row per channel with activity', () => {
    analyticsStub.refundsSummary.mockReturnValue(of(makeSummary({
      totals: {
        source: 'ALL', refunds_count: 3, refunded_amount_mxn: 250,
        realized_orders_count: 30, refund_rate_percent: 10.0,
      },
      by_channel: [
        // Zero-activity FULCRUM should be hidden.
        { source: 'FULCRUM', refunds_count: 0, refunded_amount_mxn: 0, realized_orders_count: 0, refund_rate_percent: null },
        { source: 'MERCADOLIBRE', refunds_count: 2, refunded_amount_mxn: 150, realized_orders_count: 20, refund_rate_percent: 10.0 },
        { source: 'AMAZON', refunds_count: 1, refunded_amount_mxn: 100, realized_orders_count: 10, refund_rate_percent: 10.0 },
      ],
    })));
    component.refresh();
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('[data-testid="refunds-channel-FULCRUM"]'))).toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="refunds-channel-MERCADOLIBRE"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="refunds-channel-AMAZON"]'))).not.toBeNull();
  });

  it('rateClass() flags 5%+ as high, 2-4.99% as warn, otherwise ok', () => {
    expect(component.rateClass(0)).toBe('rate-ok');
    expect(component.rateClass(1.9)).toBe('rate-ok');
    expect(component.rateClass(2)).toBe('rate-warn');
    expect(component.rateClass(4.99)).toBe('rate-warn');
    expect(component.rateClass(5)).toBe('rate-high');
    expect(component.rateClass(50)).toBe('rate-high');
    expect(component.rateClass(null)).toBe('');
  });

  it('shows an error state when the request fails on first load', () => {
    // The default mock fired on ngOnInit and populated `summary`. The
    // error template only shows when `!summary`, so clear it first to
    // simulate the "first load failed" path the operator actually sees.
    component.summary = null;
    analyticsStub.refundsSummary.mockReturnValue(throwError(() => new Error('500')));
    component.refresh();
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('[data-testid="refunds-widget-error"]'))).not.toBeNull();
  });

  it('channelLabel() formats the source codes for display', () => {
    expect(component.channelLabel('MERCADOLIBRE')).toBe('MercadoLibre');
    expect(component.channelLabel('AMAZON')).toBe('Amazon');
    expect(component.channelLabel('FULCRUM')).toBe('Fulcrum');
    expect(component.channelLabel('UNKNOWN')).toBe('UNKNOWN');
  });
});
