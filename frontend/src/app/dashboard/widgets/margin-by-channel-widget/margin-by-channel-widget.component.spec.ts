import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { MarginByChannelWidgetComponent } from './margin-by-channel-widget.component';
import {
  AnalyticsReportsService,
  CostRollupByChannelRow,
  CostRollupByChannelResponse,
} from '../../services/analytics-reports.service';

function channelRow(overrides: Partial<CostRollupByChannelRow> = {}): CostRollupByChannelRow {
  return {
    window_days: 30,
    source: 'AMAZON',
    orders: 1,
    revenue_amount_mxn: 100,
    cogs_amount: 20,
    marketplace_fees_amount: 15,
    shipping_cost_amount: 5,
    ad_spend_amount: 0,
    other_cost_amount: 0,
    total_cost_amount: 40,
    net_profit_amount: 60,
    net_margin_percent: 60,
    ...overrides,
  };
}

function listResp(channels: CostRollupByChannelRow[]): CostRollupByChannelResponse {
  return { window_days: 30, channels };
}

describe('MarginByChannelWidgetComponent', () => {
  let fixture: ComponentFixture<MarginByChannelWidgetComponent>;
  let component: MarginByChannelWidgetComponent;
  let analyticsStub: { costRollupByChannel: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    analyticsStub = {
      costRollupByChannel: vi.fn().mockReturnValue(of(listResp([]))),
    };
    await TestBed.configureTestingModule({
      imports: [
        MarginByChannelWidgetComponent,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [{ provide: AnalyticsReportsService, useValue: analyticsStub }],
    }).compileComponents();
    fixture = TestBed.createComponent(MarginByChannelWidgetComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('calls the by-channel endpoint with the default 30d window', () => {
    expect(analyticsStub.costRollupByChannel).toHaveBeenCalledWith(30);
  });

  it('renders empty state when no channels have orders', () => {
    expect(fixture.debugElement.query(By.css('[data-testid="margin-by-channel-empty"]'))).not.toBeNull();
  });

  it('renders a row per channel', () => {
    analyticsStub.costRollupByChannel.mockReturnValue(of(listResp([
      channelRow({ source: 'AMAZON' }),
      channelRow({ source: 'MERCADOLIBRE', revenue_amount_mxn: 50 }),
    ])));
    component.refresh();
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('[data-testid="channel-row-AMAZON"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="channel-row-MERCADOLIBRE"]'))).not.toBeNull();
  });

  it('segments() converts each cost component to a percentage of revenue', () => {
    const segs = component.segments(channelRow({
      revenue_amount_mxn: 100,
      cogs_amount: 20, marketplace_fees_amount: 15, shipping_cost_amount: 5,
      ad_spend_amount: 0, other_cost_amount: 0,
      total_cost_amount: 40, net_profit_amount: 60,
    }));
    const byKind = Object.fromEntries(segs.map(s => [s.kind, s.pct]));
    expect(byKind['cogs']).toBe(20);
    expect(byKind['fees']).toBe(15);
    expect(byKind['shipping']).toBe(5);
    expect(byKind['profit']).toBe(60);
    // No ads or other → those segments are omitted (not 0-width).
    expect(byKind['ads']).toBeUndefined();
    expect(byKind['other']).toBeUndefined();
    // Total adds to 100%.
    expect(segs.reduce((a, s) => a + s.pct, 0)).toBeCloseTo(100, 4);
  });

  it('segments() emits a loss bar when total cost exceeds revenue', () => {
    const segs = component.segments(channelRow({
      revenue_amount_mxn: 100,
      cogs_amount: 80, marketplace_fees_amount: 40,
      shipping_cost_amount: 0, ad_spend_amount: 0, other_cost_amount: 0,
      total_cost_amount: 120, net_profit_amount: -20, net_margin_percent: -20,
    }));
    const kinds = segs.map(s => s.kind);
    expect(kinds).toContain('loss');
    expect(kinds).not.toContain('profit');
  });

  it('segments() returns empty when revenue is 0 (avoid divide-by-zero)', () => {
    expect(component.segments(channelRow({
      revenue_amount_mxn: 0,
    }))).toEqual([]);
  });

  it('error state renders the error label, no crash', () => {
    // Tear down + recreate with the error mock active so ngOnInit
    // lands directly in the error state (the widget keeps stale
    // data on subsequent refresh failures).
    fixture.destroy();
    analyticsStub.costRollupByChannel.mockReturnValue(throwError(() => new Error('boom')));
    fixture = TestBed.createComponent(MarginByChannelWidgetComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('[data-testid="margin-by-channel-error"]'))).not.toBeNull();
  });
});
