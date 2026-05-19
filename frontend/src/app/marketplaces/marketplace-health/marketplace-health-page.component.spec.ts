import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { MarketplaceHealthPageComponent } from './marketplace-health-page.component';
import {
  HealthListResponse,
  MarketplaceCredentialHealth,
  MarketplaceHealthService,
  PollOrdersResult,
  ReconcileInboundResult,
} from './marketplace-health.service';

function row(overrides: Partial<MarketplaceCredentialHealth> = {}): MarketplaceCredentialHealth {
  return {
    credential_id: 1,
    marketplace_id: 1,
    marketplace_name: 'Amazon',
    user_id: 99,
    needs_reauthorization: false,
    last_refresh_error: null,
    expires_at: null,
    last_orders_polled_at: '2026-05-18T10:00:00Z',
    orders_poll_stale: false,
    inbound_open_count: 0,
    inbound_stale_count: 0,
    ...overrides,
  };
}

function listResponse(items: MarketplaceCredentialHealth[]): HealthListResponse {
  return {
    items,
    order_poll_stale_minutes: 30,
    inbound_reconcile_stale_minutes: 90,
  };
}

describe('MarketplaceHealthPageComponent', () => {
  let fixture: ComponentFixture<MarketplaceHealthPageComponent>;
  let component: MarketplaceHealthPageComponent;
  let serviceStub: {
    list: ReturnType<typeof vi.fn>;
    pollOrders: ReturnType<typeof vi.fn>;
    reconcileInbound: ReturnType<typeof vi.fn>;
  };

  beforeEach(async () => {
    serviceStub = {
      list: vi.fn().mockReturnValue(of(listResponse([]))),
      pollOrders: vi.fn().mockReturnValue(of({
        credential_id: 1, marketplace_name: 'Amazon',
        orders_new: 0, orders_updated: 0, orders_skipped: 0, items_created: 0,
      } as PollOrdersResult)),
      reconcileInbound: vi.fn().mockReturnValue(of({
        credential_id: 1, marketplace_name: 'Amazon',
        transfers_processed: 0, transfers_updated: 0,
        total_received_added: 0, per_transfer: [],
      } as ReconcileInboundResult)),
    };

    await TestBed.configureTestingModule({
      imports: [
        MarketplaceHealthPageComponent,
        NoopAnimationsModule,
        RouterTestingModule,
        MatSnackBarModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: MarketplaceHealthService, useValue: serviceStub },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(MarketplaceHealthPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('loads on init and shows the empty state when no credentials exist', () => {
    expect(serviceStub.list).toHaveBeenCalledTimes(1);
    expect(fixture.debugElement.query(By.css('[data-testid="health-empty-state"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="health-table"]'))).toBeNull();
  });

  it('renders one row per credential and surfaces the staleness thresholds from the response', () => {
    serviceStub.list.mockReturnValue(of(listResponse([
      row({ credential_id: 1, marketplace_name: 'Amazon' }),
      row({ credential_id: 2, marketplace_name: 'MercadoLibre' }),
    ])));
    component.refresh();
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('[data-testid="health-row-1"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="health-row-2"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="health-empty-state"]'))).toBeNull();
    expect(component.orderPollStaleMinutes).toBe(30);
    expect(component.inboundReconcileStaleMinutes).toBe(90);
  });

  it('pollOrders() patches the row in-place from the embedded health payload', () => {
    serviceStub.list.mockReturnValue(of(listResponse([row({
      credential_id: 1,
      last_orders_polled_at: '2026-05-18T08:00:00Z',
      orders_poll_stale: true,
    })])));
    component.refresh();
    fixture.detectChanges();

    serviceStub.pollOrders.mockReturnValue(of({
      credential_id: 1, marketplace_name: 'Amazon',
      orders_new: 2, orders_updated: 1, orders_skipped: 0, items_created: 4,
      health: row({
        credential_id: 1,
        last_orders_polled_at: '2026-05-18T11:00:00Z',
        orders_poll_stale: false,
      }),
    } as PollOrdersResult));

    component.pollOrders(component.rows[0]);
    expect(serviceStub.pollOrders).toHaveBeenCalledWith(1);
    // The endpoint embeds a refreshed health row — the component
    // patches that row into `rows` so the cursor + staleness chip
    // update without a follow-up GET.
    expect(component.rows[0].last_orders_polled_at).toBe('2026-05-18T11:00:00Z');
    expect(component.rows[0].orders_poll_stale).toBe(false);
    expect(component.lastPollResult.get(1)?.orders_new).toBe(2);
  });

  it('reconcileInbound() records the per-credential result and updates the row', () => {
    serviceStub.list.mockReturnValue(of(listResponse([row({
      credential_id: 1, inbound_open_count: 2, inbound_stale_count: 1,
    })])));
    component.refresh();
    fixture.detectChanges();

    serviceStub.reconcileInbound.mockReturnValue(of({
      credential_id: 1, marketplace_name: 'Amazon',
      transfers_processed: 2, transfers_updated: 1,
      total_received_added: 5,
      per_transfer: [],
      health: row({
        credential_id: 1, inbound_open_count: 2, inbound_stale_count: 0,
      }),
    } as ReconcileInboundResult));

    component.reconcileInbound(component.rows[0]);
    expect(serviceStub.reconcileInbound).toHaveBeenCalledWith(1);
    expect(component.lastReconcileResult.get(1)?.transfers_updated).toBe(1);
    expect(component.rows[0].inbound_stale_count).toBe(0);
  });

  it('pollOrders() is a no-op while a previous poll for the same row is in flight', () => {
    component.rows = [row({ credential_id: 1 })];
    component.polling.add(1);
    component.pollOrders(component.rows[0]);
    expect(serviceStub.pollOrders).not.toHaveBeenCalled();
  });

  it('reconcileInbound() is a no-op while a previous reconcile for the same row is in flight', () => {
    component.rows = [row({ credential_id: 1 })];
    component.reconciling.add(1);
    component.reconcileInbound(component.rows[0]);
    expect(serviceStub.reconcileInbound).not.toHaveBeenCalled();
  });

  it('records the needs_reauthorization error from the poll response so the UI can show it', () => {
    component.rows = [row({ credential_id: 1, needs_reauthorization: true })];
    serviceStub.pollOrders.mockReturnValue(of({
      credential_id: 1, marketplace_name: 'Amazon',
      orders_new: 0, orders_updated: 0, orders_skipped: 0, items_created: 0,
      error: 'needs_reauthorization',
    } as PollOrdersResult));
    component.pollOrders(component.rows[0]);
    expect(component.lastPollResult.get(1)?.error).toBe('needs_reauthorization');
  });

  it('classifier helpers map state correctly for the row pills', () => {
    expect(component.authClass(row({ needs_reauthorization: false }))).toBe('badge-ok');
    expect(component.authClass(row({ needs_reauthorization: true }))).toBe('badge-error');

    expect(component.pollClass(row({ orders_poll_stale: false }))).toBe('badge-ok');
    expect(component.pollClass(row({ orders_poll_stale: true }))).toBe('badge-warn');

    expect(component.inboundClass(row({ inbound_open_count: 0 }))).toBe('badge-ok');
    expect(component.inboundClass(row({ inbound_open_count: 2, inbound_stale_count: 0 }))).toBe('badge-info');
    expect(component.inboundClass(row({ inbound_open_count: 2, inbound_stale_count: 1 }))).toBe('badge-warn');
  });

  it("ago() returns 'Never' for null and a relative string for a recent timestamp", () => {
    expect(component.ago(null)).toBeTruthy();
    expect(component.ago(undefined)).toBeTruthy();
    const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    expect(component.ago(fiveMinAgo)).toMatch(/m/);
  });

  it('isBusy() is true when a poll OR reconcile is in flight for that row', () => {
    const r = row({ credential_id: 1 });
    expect(component.isBusy(r)).toBe(false);
    component.polling.add(1);
    expect(component.isBusy(r)).toBe(true);
    component.polling.delete(1);
    component.reconciling.add(1);
    expect(component.isBusy(r)).toBe(true);
  });

  it('a failed list() leaves rows empty and stops loading', () => {
    serviceStub.list.mockReturnValueOnce(throwError(() => new Error('boom')));
    component.refresh();
    fixture.detectChanges();
    expect(component.rows.length).toBe(0);
    expect(component.loading).toBe(false);
  });
});
