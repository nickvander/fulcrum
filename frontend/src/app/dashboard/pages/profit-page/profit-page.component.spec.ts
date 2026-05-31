import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { of } from 'rxjs';

import { getTranslocoTestingModule } from '../../../testing/transloco-testing';
import { ProfitPageComponent } from './profit-page.component';
import { AnalyticsReportsService } from '../../services/analytics-reports.service';

describe('ProfitPageComponent', () => {
  let fixture: ComponentFixture<ProfitPageComponent>;

  beforeEach(async () => {
    const analyticsStub = {
      profitSummary: vi.fn().mockReturnValue(
        of({
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
        }),
      ),
    };
    await TestBed.configureTestingModule({
      imports: [
        ProfitPageComponent,
        NoopAnimationsModule,
        RouterTestingModule,
        getTranslocoTestingModule(),
      ],
      providers: [{ provide: AnalyticsReportsService, useValue: analyticsStub }],
    }).compileComponents();
    fixture = TestBed.createComponent(ProfitPageComponent);
    fixture.detectChanges();
  });

  it('renders the page header and embeds the profit-summary widget', () => {
    expect(fixture.debugElement.query(By.css('[data-testid="profit-page-back"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="profit-summary-widget"]'))).not.toBeNull();
  });
});
