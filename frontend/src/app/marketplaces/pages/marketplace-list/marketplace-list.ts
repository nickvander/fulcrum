import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';

type TranslateFn = (key: string, params?: Record<string, unknown>) => string;
import { MarketplacesService, Marketplace, MarketplaceSummary } from '../../marketplaces';
import {
  MarketplaceCatalogService,
  MarketplaceCatalogEntry,
} from '../../marketplace-catalog.service';
import { combineLatest, forkJoin, Observable, of } from 'rxjs';
import { catchError, map, switchMap } from 'rxjs/operators';

export interface MarketplaceCardModel extends Marketplace {
  summary: MarketplaceSummary | null;
}

/**
 * A catalog channel + whichever DB marketplace row backs it (null if
 * the workspace hasn't connected it yet). The channel list itself comes
 * from the backend catalog (`/marketplace/catalog`) — there's no
 * hardcoded list here, so a marketplace added to the catalog
 * automatically appears on this page in priority order.
 *
 * `comingSoon` channels (those that aren't connectable yet, e.g. eBay)
 * render as a planned-channel card instead of a dead "Connect" button.
 */
export interface ChannelViewModel {
  key: string;
  displayName: string;
  primary: boolean;
  comingSoon: boolean;
  brandColor: string;
  marketplace: MarketplaceCardModel | null;
}

@Component({
  selector: 'app-marketplace-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatDividerModule,
    MatSnackBarModule,
    MatTooltipModule,
    TranslocoModule
  ],
  templateUrl: './marketplace-list.html',
  styleUrl: './marketplace-list.scss',
})
export class MarketplaceListComponent implements OnInit {
  /** Channel cards, catalog-ordered (primary first). */
  channels$: Observable<ChannelViewModel[]> = of([]);
  /** Raw catalog — drives the add-channel dialog options. */
  catalog$: Observable<MarketplaceCatalogEntry[]> = of([]);
  syncing = false;
  showAddDialog = false;

  constructor(
    private marketplaceService: MarketplacesService,
    private catalogService: MarketplaceCatalogService,
    private snackBar: MatSnackBar,
    private transloco: TranslocoService
  ) { }

  ngOnInit(): void {
    this.catalog$ = this.catalogService.getCatalog();
    this.refresh();
  }

  refresh(): void {
    this.channels$ = this.loadChannels();
  }

  /**
   * Project the backend catalog onto the connected marketplaces so
   * every catalog channel always has a card (connected or not), in the
   * catalog's priority order. No hardcoded channel list — adding a
   * marketplace to the catalog is enough to make it appear here.
   */
  private loadChannels(): Observable<ChannelViewModel[]> {
    return combineLatest([this.catalogService.getCatalog(), this.loadCards()]).pipe(
      map(([catalog, cards]) =>
        catalog.map((entry) => this.toChannelViewModel(entry, cards)),
      ),
    );
  }

  private toChannelViewModel(
    entry: MarketplaceCatalogEntry,
    cards: MarketplaceCardModel[],
  ): ChannelViewModel {
    return {
      key: entry.key,
      displayName: entry.display_name,
      primary: entry.is_primary,
      // Not connectable yet (planned / no OAuth) → render as coming soon.
      comingSoon: !entry.is_connectable,
      brandColor: entry.brand_color,
      marketplace:
        cards.find((c) => c.name.toLowerCase().includes(entry.key))
        // MercadoLibre's DB row is named "MercadoLibre"; match on the
        // common stem so the slug ('mercadolibre') still resolves it.
        ?? cards.find(
          (c) => entry.key === 'mercadolibre' && c.name.toLowerCase().includes('mercado'),
        )
        ?? null,
    };
  }

  private loadCards(): Observable<MarketplaceCardModel[]> {
    return this.marketplaceService.getMarketplaces().pipe(
      switchMap((markets) => {
        if (markets.length === 0) {
          return of([] as MarketplaceCardModel[]);
        }
        return forkJoin(
          markets.map((m) =>
            this.marketplaceService.getMarketplaceSummary(m.id).pipe(
              map((summary): MarketplaceCardModel => ({ ...m, summary })),
              catchError(() => of<MarketplaceCardModel>({ ...m, summary: null }))
            )
          )
        );
      }),
      catchError(() => of([] as MarketplaceCardModel[])),
    );
  }

  /** Connected = backed by a DB marketplace with a live credential. */
  isConnected(vm: ChannelViewModel): boolean {
    return !!vm.marketplace?.summary?.credential_connected;
  }

  /** Route to the connect / settings flow for this channel. */
  connectRoute(vm: ChannelViewModel): string {
    return `/marketplaces/settings/${vm.key}`;
  }

  syncMarketplace(marketplaceId: number): void {
    this.syncing = true;
    const close = this.transloco.translate('common.close');
    this.marketplaceService.importListings(marketplaceId).subscribe({
      next: (stats) => {
        this.syncing = false;
        const msg = this.transloco.translate('marketing.messages.syncCompleteSummary', {
          synced: stats.synced,
          created: stats.created_product_shell,
        });
        this.snackBar.open(msg, close, { duration: 5000 });
        this.refresh();
      },
      error: (err) => {
        this.syncing = false;
        console.error('Sync error:', err);
        this.snackBar.open(
          this.transloco.translate('marketing.messages.syncCheckCredentials'),
          close,
          { duration: 5000 },
        );
      }
    });
  }

  /** Logo path for a channel — convention-based via the catalog
   *  service (images/marketplaces/{key}.png). */
  logoFor(key: string): string {
    return this.catalogService.logoFor(key);
  }

  /** Connect / settings route for a catalog entry by slug. */
  connectRouteForKey(key: string): string {
    return `/marketplaces/settings/${key}`;
  }

  /**
   * Template-friendly variant that takes the Transloco `t` function out of
   * `*transloco="let t"`. Keeps reactive language switching working.
   */
  formatLastSyncTranslated(iso: string | null | undefined, t: TranslateFn): string {
    if (!iso) {
      return t('marketing.neverSynced');
    }
    const synced = new Date(iso);
    const diffMs = Date.now() - synced.getTime();
    const minutes = Math.floor(diffMs / 60_000);
    if (minutes < 1) return t('marketing.syncedJustNow');
    if (minutes < 60) return t('marketing.syncedMinutesAgo', { minutes });
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return t('marketing.syncedHoursAgo', { hours });
    const days = Math.floor(hours / 24);
    return t('marketing.syncedDaysAgo', { days });
  }

  tokenChipState(summary: MarketplaceSummary | null): 'ok' | 'warning' | 'expired' | 'disconnected' | 'reauth' | 'none' {
    if (!summary) return 'none';
    if (!summary.credential_connected) return 'disconnected';
    // Reauth state takes precedence over expiry — a marked credential
    // can't be refreshed in-process, so showing "expires in 6 days" is
    // misleading. The chip + tooltip must surface the reauth state.
    if (summary.needs_reauthorization) return 'reauth';
    if (summary.token_expires_in_days == null) return 'ok';
    if (summary.token_expires_in_days < 0) return 'expired';
    if (summary.token_expires_in_days <= 3) return 'warning';
    return 'ok';
  }

  tokenChipLabelTranslated(summary: MarketplaceSummary | null, t: TranslateFn): string {
    const state = this.tokenChipState(summary);
    if (state === 'none') return '';
    if (state === 'disconnected') return t('marketing.notConnected');
    if (state === 'reauth') return t('marketing.needsReauth');
    if (state === 'expired') return t('marketing.tokenExpired');
    if (state === 'warning') {
      const days = summary?.token_expires_in_days ?? 0;
      return days <= 0 ? t('marketing.tokenExpiresToday') : t('marketing.tokenExpiresInDays', { days });
    }
    return t('marketing.tokenHealthy');
  }

  /**
   * Tooltip text for the reauth chip — shows the captured backend
   * `last_refresh_error` so the operator knows WHY their token went
   * stale (invalid_grant vs network error vs revoked).
   */
  tokenChipTooltipTranslated(summary: MarketplaceSummary | null, t: TranslateFn): string {
    if (this.tokenChipState(summary) !== 'reauth') return '';
    return summary?.reauthorization_reason
      ? t('marketing.needsReauthTooltipWithReason', { reason: summary.reauthorization_reason })
      : t('marketing.needsReauthTooltip');
  }
}
