import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { ActivatedRoute } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { of } from 'rxjs';

import { MarketplaceListComponent } from './marketplace-list';
import {
  Marketplace,
  MarketplaceSummary,
  MarketplacesService,
} from '../../marketplaces';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslocoTestingModule } from '@ngneat/transloco';

function makeSummary(overrides: Partial<MarketplaceSummary> = {}): MarketplaceSummary {
  return {
    marketplace_id: 1,
    listing_count: 0,
    healthy_count: 0,
    issues_count: 0,
    last_sync_at: null,
    credential_connected: true,
    token_expires_at: null,
    token_expires_in_days: null,
    needs_reauthorization: false,
    reauthorization_reason: null,
    ...overrides,
  };
}

describe('MarketplaceListComponent', () => {
  let component: MarketplaceListComponent;
  let fixture: ComponentFixture<MarketplaceListComponent>;
  let serviceStub: {
    getMarketplaces: ReturnType<typeof vi.fn>;
    getMarketplaceSummary: ReturnType<typeof vi.fn>;
    importListings: ReturnType<typeof vi.fn>;
  };

  beforeEach(async () => {
    serviceStub = {
      getMarketplaces: vi.fn().mockReturnValue(of([])),
      getMarketplaceSummary: vi.fn().mockImplementation(() => of(makeSummary())),
      importListings: vi.fn().mockReturnValue(of({})),
    };

    await TestBed.configureTestingModule({
      imports: [
        MarketplaceListComponent,
        MatSnackBarModule,
        NoopAnimationsModule,
        RouterTestingModule,
        TranslocoTestingModule.forRoot({
          langs: {
            en: {
              marketing: {
                needsReauth: 'Reauthorize',
                needsReauthTooltip: 'Reconnect this marketplace to resume syncing.',
                needsReauthTooltipWithReason:
                  'Reconnect this marketplace to resume syncing. Reason: {{reason}}',
                reconnect: 'Reconnect',
                tokenExpired: 'Token expired',
                tokenExpiresToday: 'Token expires today',
                tokenExpiresInDays: 'Token expires in {{days}}d',
                tokenHealthy: 'Token healthy',
                notConnected: 'Not connected',
                activeConnection: 'Active connection',
                operational: 'Operational',
                statusDisconnected: 'Disconnected',
                listings: 'Listings',
                healthy: 'Healthy',
                issues: 'Issues',
                syncNow: 'Sync now',
                syncing: 'Syncing…',
                manage: 'Manage',
                marketplaceChannels: 'Marketplace Channels',
                marketplaceDesc: '',
                addMarketplace: 'Add',
                neverSynced: 'never',
                noMarketplaces: 'none',
                noMarketplacesDesc: '',
                addFirstMarketplace: 'add first',
                syncedJustNow: 'just now',
                syncedMinutesAgo: '{{minutes}}m ago',
                syncedHoursAgo: '{{hours}}h ago',
                syncedDaysAgo: '{{days}}d ago',
              },
              common: { close: 'Close', cancel: 'Cancel' },
            },
            'es-MX': {},
          },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: MarketplacesService, useValue: serviceStub },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => null } } } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(MarketplaceListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // ---------------------------------------------------------------------------
  // tokenChipState — pure-state branches
  // ---------------------------------------------------------------------------

  describe('tokenChipState', () => {
    it('returns "none" when summary is null', () => {
      expect(component.tokenChipState(null)).toBe('none');
    });

    it('returns "disconnected" when no credential', () => {
      const s = makeSummary({ credential_connected: false });
      expect(component.tokenChipState(s)).toBe('disconnected');
    });

    it('returns "reauth" when needs_reauthorization is true', () => {
      const s = makeSummary({ needs_reauthorization: true });
      expect(component.tokenChipState(s)).toBe('reauth');
    });

    it('returns "reauth" even when token has not expired — reauth wins', () => {
      // Reauth takes precedence over expiry: a marked credential cannot
      // be silently refreshed, so showing "expires in 6 days" would be
      // misleading. This is a regression test for that precedence.
      const s = makeSummary({
        needs_reauthorization: true,
        token_expires_in_days: 6,
      });
      expect(component.tokenChipState(s)).toBe('reauth');
    });

    it('returns "expired" when token_expires_in_days is negative', () => {
      const s = makeSummary({ token_expires_in_days: -2 });
      expect(component.tokenChipState(s)).toBe('expired');
    });

    it('returns "warning" when token_expires_in_days is <= 3', () => {
      const s = makeSummary({ token_expires_in_days: 2 });
      expect(component.tokenChipState(s)).toBe('warning');
    });

    it('returns "ok" when token_expires_in_days is comfortably positive', () => {
      const s = makeSummary({ token_expires_in_days: 30 });
      expect(component.tokenChipState(s)).toBe('ok');
    });
  });

  // ---------------------------------------------------------------------------
  // Tooltip — reauth-specific branch carries the captured refresh reason
  // ---------------------------------------------------------------------------

  describe('tokenChipTooltipTranslated', () => {
    const t = (key: string, params?: Record<string, unknown>): string => {
      if (key === 'marketing.needsReauthTooltipWithReason') {
        return `Reconnect this marketplace to resume syncing. Reason: ${params?.['reason']}`;
      }
      if (key === 'marketing.needsReauthTooltip') {
        return 'Reconnect this marketplace to resume syncing.';
      }
      return '';
    };

    it('returns empty when chip is not in the reauth state', () => {
      const s = makeSummary({ needs_reauthorization: false });
      expect(component.tokenChipTooltipTranslated(s, t)).toBe('');
    });

    it('returns the with-reason tooltip when last_refresh_error is present', () => {
      const s = makeSummary({
        needs_reauthorization: true,
        reauthorization_reason: 'invalid_grant',
      });
      expect(component.tokenChipTooltipTranslated(s, t))
        .toBe('Reconnect this marketplace to resume syncing. Reason: invalid_grant');
    });

    it('falls back to the plain tooltip when no reason is captured', () => {
      const s = makeSummary({
        needs_reauthorization: true,
        reauthorization_reason: null,
      });
      expect(component.tokenChipTooltipTranslated(s, t))
        .toBe('Reconnect this marketplace to resume syncing.');
    });
  });

  // ---------------------------------------------------------------------------
  // DOM — the reauth chip + warn-styled Reconnect button must render
  // ---------------------------------------------------------------------------

  describe('reauth chip in template', () => {
    function renderWithSummary(summary: MarketplaceSummary): void {
      const market: Marketplace = { id: 9, name: 'MercadoLibre' };
      serviceStub.getMarketplaces.mockReturnValue(of([market]));
      serviceStub.getMarketplaceSummary.mockReturnValue(of(summary));
      component.refresh();
      fixture.detectChanges();
    }

    it('renders the reauth chip with the "reauth" CSS class when needs_reauthorization is true', () => {
      renderWithSummary(makeSummary({
        marketplace_id: 9,
        needs_reauthorization: true,
        reauthorization_reason: 'invalid_grant',
      }));

      const chip = fixture.debugElement.query(By.css('.token-chip.reauth'));
      expect(chip).not.toBeNull();
      expect(chip.nativeElement.textContent).toContain('Reauthorize');
    });

    it('renders the warn-styled Reconnect button instead of Sync now when in the reauth state', () => {
      renderWithSummary(makeSummary({
        marketplace_id: 9,
        needs_reauthorization: true,
      }));

      const buttons = fixture.debugElement.queryAll(By.css('mat-card-actions button'));
      const labels = buttons.map((b) => (b.nativeElement.textContent || '').trim());
      expect(labels.some((l) => l.includes('Reconnect'))).toBe(true);
      expect(labels.some((l) => l.includes('Sync now'))).toBe(false);
    });

    it('renders Sync now (no Reconnect) when the credential is healthy', () => {
      renderWithSummary(makeSummary({
        marketplace_id: 9,
        needs_reauthorization: false,
        token_expires_in_days: 30,
      }));

      const buttons = fixture.debugElement.queryAll(By.css('mat-card-actions button'));
      const labels = buttons.map((b) => (b.nativeElement.textContent || '').trim());
      expect(labels.some((l) => l.includes('Sync now'))).toBe(true);
      expect(labels.some((l) => l.includes('Reconnect'))).toBe(false);

      // And the chip must NOT carry the .reauth class — the warning/ok
      // variants are visually distinct.
      const reauthChip = fixture.debugElement.query(By.css('.token-chip.reauth'));
      expect(reauthChip).toBeNull();
    });
  });
});
