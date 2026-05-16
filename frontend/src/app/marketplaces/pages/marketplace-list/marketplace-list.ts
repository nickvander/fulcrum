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
import { forkJoin, Observable, of } from 'rxjs';
import { catchError, map, switchMap } from 'rxjs/operators';

export interface MarketplaceCardModel extends Marketplace {
  summary: MarketplaceSummary | null;
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
  cards$: Observable<MarketplaceCardModel[]> = of([]);
  syncing = false;
  showAddDialog = false;

  constructor(
    private marketplaceService: MarketplacesService,
    private snackBar: MatSnackBar,
    private transloco: TranslocoService
  ) { }

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.cards$ = this.loadCards();
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
      })
    );
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

  getMarketplaceLogo(name: string): string {
    const n = name.toLowerCase();
    if (n.includes('amazon')) return 'images/marketplaces/amazon.png';
    if (n.includes('mercado')) return 'images/marketplaces/mercadolibre.png';
    return 'images/marketplaces/default.png';
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

  tokenChipState(summary: MarketplaceSummary | null): 'ok' | 'warning' | 'expired' | 'disconnected' | 'none' {
    if (!summary) return 'none';
    if (!summary.credential_connected) return 'disconnected';
    if (summary.token_expires_in_days == null) return 'ok';
    if (summary.token_expires_in_days < 0) return 'expired';
    if (summary.token_expires_in_days <= 3) return 'warning';
    return 'ok';
  }

  tokenChipLabelTranslated(summary: MarketplaceSummary | null, t: TranslateFn): string {
    const state = this.tokenChipState(summary);
    if (state === 'none') return '';
    if (state === 'disconnected') return t('marketing.notConnected');
    if (state === 'expired') return t('marketing.tokenExpired');
    if (state === 'warning') {
      const days = summary?.token_expires_in_days ?? 0;
      return days <= 0 ? t('marketing.tokenExpiresToday') : t('marketing.tokenExpiresInDays', { days });
    }
    return t('marketing.tokenHealthy');
  }
}
