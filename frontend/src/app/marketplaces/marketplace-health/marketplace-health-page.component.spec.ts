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
    webhook_last_received_at: null,
    webhooks_received_last_24h: 0,
    webhook_likely_disconnected: false,
    ...overrides,
  };
}

function listResponse(items: MarketplaceCredentialHealth[]): HealthListResponse {
  return {
    items,
    order_poll_stale_minutes: 30,
    inbound_reconcile_stale_minutes: 90,
    webhook_disconnect_hours: 24,
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
    expect(component.webhookDisconnectHours).toBe(24);
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

    // Webhook column has three states: ok (events received), warn
    // (no events in 24h but credential too fresh to flag), error
    // (subscription likely disconnected).
    expect(component.webhookClass(row({
      webhooks_received_last_24h: 5,
      webhook_likely_disconnected: false,
    }))).toBe('badge-ok');
    expect(component.webhookClass(row({
      webhooks_received_last_24h: 0,
      webhook_likely_disconnected: false,
    }))).toBe('badge-warn');
    expect(component.webhookClass(row({
      webhooks_received_last_24h: 0,
      webhook_likely_disconnected: true,
    }))).toBe('badge-error');
  });

  it('renders the webhook column with the right pill state per row', () => {
    serviceStub.list.mockReturnValue(of(listResponse([
      row({
        credential_id: 1,
        webhooks_received_last_24h: 3,
        webhook_last_received_at: '2026-05-18T11:00:00Z',
        webhook_likely_disconnected: false,
      }),
      row({
        credential_id: 2,
        webhooks_received_last_24h: 0,
        webhook_last_received_at: null,
        webhook_likely_disconnected: true,
      }),
    ])));
    component.refresh();
    fixture.detectChanges();

    const pillOne = fixture.debugElement.query(By.css('[data-testid="webhook-pill-1"]'));
    expect(pillOne).not.toBeNull();
    expect(pillOne.nativeElement.classList.contains('badge-ok')).toBe(true);

    const pillTwo = fixture.debugElement.query(By.css('[data-testid="webhook-pill-2"]'));
    expect(pillTwo).not.toBeNull();
    expect(pillTwo.nativeElement.classList.contains('badge-error')).toBe(true);
  });

  it('applyRefreshedHealth() updates the webhook flags after a poll', () => {
    serviceStub.list.mockReturnValue(of(listResponse([row({
      credential_id: 1,
      webhook_likely_disconnected: true,
      webhooks_received_last_24h: 0,
    })])));
    component.refresh();
    fixture.detectChanges();

    serviceStub.pollOrders.mockReturnValue(of({
      credential_id: 1, marketplace_name: 'Amazon',
      orders_new: 1, orders_updated: 0, orders_skipped: 0, items_created: 1,
      health: row({
        credential_id: 1,
        webhook_likely_disconnected: false,
        webhooks_received_last_24h: 2,
        webhook_last_received_at: '2026-05-18T12:00:00Z',
      }),
    } as PollOrdersResult));

    component.pollOrders(component.rows[0]);
    expect(component.rows[0].webhook_likely_disconnected).toBe(false);
    expect(component.rows[0].webhooks_received_last_24h).toBe(2);
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

  // ---------------- auto-refresh ----------------

  // The component subscribes to `interval()` during ngOnInit. Fake
  // timers must be installed BEFORE that subscription so the rxjs
  // scheduler picks them up; otherwise the interval handle is on the
  // real clock and `vi.advanceTimersByTime` does nothing. Each test
  // in this block destroys the outer fixture first, installs fakes,
  // then creates a fresh fixture.
  describe('auto-refresh', () => {
    beforeEach(() => {
      // Tear down the fixture the outer beforeEach created on real
      // timers — we'll recreate it on fakes below.
      fixture.destroy();
      vi.useFakeTimers();
      // Reset the call counter so each test starts from 0.
      serviceStub.list.mockClear();
      serviceStub.list.mockReturnValue(of(listResponse([])));
      fixture = TestBed.createComponent(MarketplaceHealthPageComponent);
      component = fixture.componentInstance;
      fixture.detectChanges();  // triggers ngOnInit with fakes active
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('polls the list at the auto-refresh cadence while the page is open', () => {
      // After ngOnInit there's exactly 1 call (the initial refresh).
      expect(serviceStub.list).toHaveBeenCalledTimes(1);

      vi.advanceTimersByTime(component.AUTO_REFRESH_MS);
      expect(serviceStub.list).toHaveBeenCalledTimes(2);
      vi.advanceTimersByTime(component.AUTO_REFRESH_MS);
      expect(serviceStub.list).toHaveBeenCalledTimes(3);
    });

    it('quiet refresh does NOT toggle the loading spinner', () => {
      // After ngOnInit refresh resolves synchronously (mock returns
      // `of(...)` immediately), `loading` is back to false.
      expect(component.loading).toBe(false);
      // The auto-tick should leave loading at false — the operator
      // shouldn't see the table flash a spinner every 45s.
      vi.advanceTimersByTime(component.AUTO_REFRESH_MS);
      expect(component.loading).toBe(false);
    });

    it('skips the auto-tick when a per-row action is in flight to avoid clobbering the embedded health patch', () => {
      // Pretend a poll is in flight on row 1.
      component.rows = [row({ credential_id: 1 })];
      component.polling.add(1);
      expect(serviceStub.list).toHaveBeenCalledTimes(1);

      vi.advanceTimersByTime(component.AUTO_REFRESH_MS);
      expect(serviceStub.list).toHaveBeenCalledTimes(1);  // skipped
      vi.advanceTimersByTime(component.AUTO_REFRESH_MS);
      expect(serviceStub.list).toHaveBeenCalledTimes(1);  // still skipped

      // Once the action clears, the next tick fires.
      component.polling.delete(1);
      vi.advanceTimersByTime(component.AUTO_REFRESH_MS);
      expect(serviceStub.list).toHaveBeenCalledTimes(2);
    });

    it('skips while a reconcile is in flight too — the busy-check covers both action types', () => {
      component.reconciling.add(7);
      expect(serviceStub.list).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(component.AUTO_REFRESH_MS * 3);
      expect(serviceStub.list).toHaveBeenCalledTimes(1);
    });

    it('a failing auto-tick stays silent (no snackbar) so a transient hiccup does not spam the operator', () => {
      const snackSpy = vi.spyOn(
        component as unknown as { snack: (k: string) => void },
        'snack',
      );
      serviceStub.list.mockReturnValueOnce(throwError(() => new Error('blip')));
      vi.advanceTimersByTime(component.AUTO_REFRESH_MS);
      expect(snackSpy).not.toHaveBeenCalled();
    });

    it('tears down the timer on destroy so navigating away does not leak HTTP requests', () => {
      expect(serviceStub.list).toHaveBeenCalledTimes(1);
      fixture.destroy();
      vi.advanceTimersByTime(component.AUTO_REFRESH_MS * 5);
      expect(serviceStub.list).toHaveBeenCalledTimes(1);
    });
  });
});
