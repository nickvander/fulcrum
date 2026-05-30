import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { of } from 'rxjs';
import { ActivatedRoute } from '@angular/router';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';

import { SalesOrderDetailComponent } from './sales-order-detail';
import {
  SalesOrderDetail,
  SalesOrdersService,
} from '../../services/sales-orders.service';

describe('SalesOrderDetailComponent', () => {
  let component: SalesOrderDetailComponent;
  let fixture: ComponentFixture<SalesOrderDetailComponent>;
  let serviceStub: {
    get: ReturnType<typeof vi.fn>;
    listReturns: ReturnType<typeof vi.fn>;
  };

  function mkOrder(overrides: Partial<SalesOrderDetail> = {}): SalesOrderDetail {
    return {
      id: 42,
      status: 'COMPLETED',
      total_price: 400,
      currency: 'MXN',
      created_at: '2026-03-15T12:00:00Z',
      source: 'MERCADOLIBRE',
      external_order_id: 'ML-123',
      items: [
        {
          id: 1,
          product_id: 7,
          quantity: 2,
          price_per_unit: 200,
          cost_per_unit: 80,
          product_name: 'Widget',
          product_sku: 'W-1',
        },
      ],
      cost_breakdown: {
        currency: 'MXN',
        exchange_rate_to_mxn: 1,
        revenue_amount: 400,
        revenue_amount_mxn: 400,
        cogs_amount: 160,
        marketplace_fees_amount: 40,
        shipping_cost_amount: 0,
        ad_spend_amount: 0,
        other_cost_amount: 0,
        total_cost_amount: 200,
        net_profit_amount: 200,
        net_margin_percent: 50,
        fees_source: 'estimated',
        fees_synced_at: null,
        reversed_at: null,
      },
      status_timeline: [],
      refund_events: [],
      ...overrides,
    };
  }

  async function setup(order: SalesOrderDetail | null) {
    serviceStub = {
      get: vi.fn().mockReturnValue(of(order)),
      listReturns: vi.fn().mockReturnValue(of([])),
    };

    await TestBed.configureTestingModule({
      imports: [
        SalesOrderDetailComponent,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: SalesOrdersService, useValue: serviceStub },
        { provide: MatDialog, useValue: { open: vi.fn() } },
        { provide: MatSnackBar, useValue: { open: vi.fn() } },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => '42' } } },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SalesOrderDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  it('creates and loads the order', async () => {
    await setup(mkOrder());
    expect(component).toBeTruthy();
    expect(serviceStub.get).toHaveBeenCalledWith(42);
    expect(serviceStub.listReturns).toHaveBeenCalledWith(42);
  });

  it('renders the economics card with the net-profit row', async () => {
    await setup(mkOrder());
    const card = fixture.debugElement.query(By.css('[data-testid="order-economics"]'));
    expect(card).not.toBeNull();
    expect(card.nativeElement.textContent).toContain('MX$200.00'); // net profit
    expect(card.nativeElement.textContent).toContain('50%');       // margin pct
  });

  it('omits the economics card when no breakdown exists', async () => {
    await setup(mkOrder({ cost_breakdown: null }));
    expect(
      fixture.debugElement.query(By.css('[data-testid="order-economics"]')),
    ).toBeNull();
  });

  // ---------------- margin helpers ----------------

  it('marginClass() bands by profitability', () => {
    expect(component.marginClass(-2)).toBe('margin-loss');
    expect(component.marginClass(5)).toBe('margin-thin');
    expect(component.marginClass(25)).toBe('margin-healthy');
    expect(component.marginClass(null)).toBe('');
  });

  it('lineMargin() multiplies the per-unit spread by quantity', () => {
    expect(component.lineMargin({ price_per_unit: 200, cost_per_unit: 80, quantity: 2 })).toBe(240);
  });

  it('lineMargin() returns null when no cost basis is captured', () => {
    expect(component.lineMargin({ price_per_unit: 200, cost_per_unit: null, quantity: 2 })).toBeNull();
  });

  // ---------------- MXN equivalent ----------------

  it('showMxnEquivalent() only fires for non-MXN orders with a breakdown', async () => {
    await setup(mkOrder());
    expect(component.showMxnEquivalent(component.order)).toBe(false); // MXN
    const usd = mkOrder({
      currency: 'USD',
      cost_breakdown: { ...mkOrder().cost_breakdown!, currency: 'USD', exchange_rate_to_mxn: 18, revenue_amount_mxn: 7200 },
    });
    expect(component.showMxnEquivalent(usd)).toBe(true);
    expect(component.showMxnEquivalent(null)).toBe(false);
  });

  it('renders the MXN-equivalent line for a USD order', async () => {
    await setup(
      mkOrder({
        currency: 'USD',
        cost_breakdown: {
          ...mkOrder().cost_breakdown!,
          currency: 'USD',
          exchange_rate_to_mxn: 18,
          revenue_amount: 40,
          revenue_amount_mxn: 720,
        },
      }),
    );
    expect(
      fixture.debugElement.query(By.css('[data-testid="mxn-equivalent"]')),
    ).not.toBeNull();
  });

  // ---------------- refunds + timeline ----------------

  it('renders refund events when present', async () => {
    await setup(
      mkOrder({
        refund_events: [
          { refund_id: 'RF-1', posted_at: '2026-03-20T00:00:00Z', refund_amount: 25, currency: 'MXN' },
        ],
      }),
    );
    const card = fixture.debugElement.query(By.css('[data-testid="refund-events"]'));
    expect(card).not.toBeNull();
    expect(card.nativeElement.textContent).toContain('RF-1');
  });

  it('renders the status timeline when present', async () => {
    await setup(
      mkOrder({
        status_timeline: [
          { from_status: null, to_status: 'PAID', changed_at: '2026-03-15T12:00:00Z', source_signal: 'ml_poll' },
          { from_status: 'PAID', to_status: 'SHIPPED', changed_at: '2026-03-16T12:00:00Z', source_signal: 'ml_poll' },
        ],
      }),
    );
    const card = fixture.debugElement.query(By.css('[data-testid="status-timeline"]'));
    expect(card).not.toBeNull();
    const rows = card.queryAll(By.css('.timeline-row'));
    expect(rows.length).toBe(2);
  });
});
