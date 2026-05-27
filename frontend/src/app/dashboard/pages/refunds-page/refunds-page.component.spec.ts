import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { RefundsPageComponent } from './refunds-page.component';
import {
  AnalyticsReportsService,
  RefundsListResponse,
} from '../../services/analytics-reports.service';

function makeListResponse(over: Partial<RefundsListResponse> = {}): RefundsListResponse {
  return {
    window_label: 'window 30d',
    items: [],
    total: 0,
    ...over,
  };
}

describe('RefundsPageComponent', () => {
  let fixture: ComponentFixture<RefundsPageComponent>;
  let component: RefundsPageComponent;
  let analyticsStub: { refundsList: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    analyticsStub = {
      refundsList: vi.fn().mockReturnValue(of(makeListResponse())),
    };

    await TestBed.configureTestingModule({
      imports: [
        RefundsPageComponent,
        NoopAnimationsModule,
        RouterTestingModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: AnalyticsReportsService, useValue: analyticsStub },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(RefundsPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('loads on init with default window=30 and no source filter', () => {
    expect(analyticsStub.refundsList).toHaveBeenCalledWith(30, 0, 50, undefined);
  });

  it('renders the empty state when no rows are returned', () => {
    const empty = fixture.debugElement.query(By.css('[data-testid="refunds-page-empty"]'));
    expect(empty).not.toBeNull();
  });

  it('renders one row per item with the right kind chip + link', () => {
    analyticsStub.refundsList.mockReturnValue(of(makeListResponse({
      total: 2,
      items: [
        {
          refund_kind: 'order_cancelled',
          order_id: 11,
          source: 'MERCADOLIBRE',
          external_order_id: 'ML-A',
          refunded_at: '2026-05-19T10:00:00Z',
          refunded_amount_mxn: 150.5,
          order_status: 'CANCELLED',
        },
        {
          refund_kind: 'amazon_partial',
          order_id: 12,
          source: 'AMAZON',
          external_order_id: 'AMZ-B',
          refunded_at: '2026-05-19T11:00:00Z',
          refunded_amount_mxn: 25,
          order_status: 'SHIPPED',
        },
      ],
    })));
    component.load();
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('[data-testid="refunds-row-11"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="refunds-row-12"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="refunds-row-link-11"]'))).not.toBeNull();
  });

  it('changing the source filter resets to page 0 and re-loads', () => {
    component.pageIndex = 3;
    component.sourceFilter = 'AMAZON';
    component.onFilterChange();

    expect(component.pageIndex).toBe(0);
    expect(analyticsStub.refundsList).toHaveBeenLastCalledWith(30, 0, 50, 'amazon');
  });

  it('changing the window resets to page 0 and forwards the new window', () => {
    component.pageIndex = 2;
    component.windowDays = 90;
    component.onFilterChange();

    expect(component.pageIndex).toBe(0);
    expect(analyticsStub.refundsList).toHaveBeenLastCalledWith(90, 0, 50, undefined);
  });

  it('paginator events update skip + pageSize and re-load', () => {
    component.onPage({ pageIndex: 2, pageSize: 25, length: 100 } as any);
    expect(component.pageIndex).toBe(2);
    expect(component.pageSize).toBe(25);
    expect(analyticsStub.refundsList).toHaveBeenLastCalledWith(30, 50, 25, undefined);
  });

  it('shows an error card when the request fails', () => {
    component.rows = [];  // simulate first load
    analyticsStub.refundsList.mockReturnValue(throwError(() => new Error('500')));
    component.load();
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('[data-testid="refunds-page-error"]'))).not.toBeNull();
    expect(component.errored).toBe(true);
  });

  it('refundKindClass() maps the discriminator to a chip class', () => {
    expect(component.refundKindClass('order_cancelled')).toBe('chip-cancelled');
    expect(component.refundKindClass('amazon_partial')).toBe('chip-partial');
  });

  it('channelLabel() formats source codes for display', () => {
    expect(component.channelLabel('MERCADOLIBRE')).toBe('MercadoLibre');
    expect(component.channelLabel('AMAZON')).toBe('Amazon');
    expect(component.channelLabel('FULCRUM')).toBe('Fulcrum');
    expect(component.channelLabel('SHOPIFY')).toBe('SHOPIFY');
  });
});
