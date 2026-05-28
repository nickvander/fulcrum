import { Component } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Observable } from 'rxjs';
import { map, shareReplay, filter, delay } from 'rxjs/operators';

import { Router, NavigationEnd } from '@angular/router';
import { AsyncPipe } from '@angular/common';
import { MatSidenavModule } from '@angular/material/sidenav';
import { RouterModule } from '@angular/router';
import { CoreModule } from './core/core-module';
import { LoadingService } from './core/services/loading.service';
import { ScreenService } from './core/services/screen.service';
import { SettingsService } from './core/services/settings.service';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslocoService } from '@ngneat/transloco';
import { DateAdapter, MatNativeDateModule } from '@angular/material/core';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    AsyncPipe,
    MatSidenavModule,
    RouterModule,
    CoreModule,
    MatProgressSpinnerModule,
    MatNativeDateModule
  ],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  isMobile$: Observable<boolean>;
  isMobileOrTablet$: Observable<boolean>;
  isDesktop$: Observable<boolean>;
  isLoginPage = false;
  loading$: Observable<boolean>;

  constructor(
    private router: Router,
    private loadingService: LoadingService,
    private screenService: ScreenService,
    private settingsService: SettingsService,
    private translocoService: TranslocoService,
    private dateAdapter: DateAdapter<Date>
  ) {
    this.isMobile$ = this.screenService.isMobile$;
    this.isMobileOrTablet$ = this.screenService.isMobileOrTablet$;
    this.isDesktop$ = this.screenService.isDesktop$;

    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe(event => {
      const navEnd = event as NavigationEnd;
      this.isLoginPage = navEnd.url === '/login';
      // URL-driven locale switch: deep-link / share / smoke-test
      // friendly. `?lang=es-MX` (anywhere in the app) sets the
      // active language AND persists it into localStorage via the
      // settings service so the next visit retains it. Invalid
      // codes are ignored.
      this.applyUrlLangParam(navEnd.url);
    });

    this.loading$ = this.loadingService.loading$.pipe(delay(0));

    // Subscribe to theme and language changes
    this.settingsService.settings$.subscribe(settings => {
      if (settings?.theme === 'dark') {
        document.body.classList.add('dark-theme');
      } else {
        document.body.classList.remove('dark-theme');
      }

      const lang = settings?.language || 'en';
      this.translocoService.setActiveLang(lang);
      this.dateAdapter.setLocale(lang);
    });

    // Subscribe to language changes to update date adapter
    this.translocoService.langChanges$.subscribe(lang => {
      this.dateAdapter.setLocale(lang);
    });
  }

  /** Pull `?lang=` out of the URL and, if it's a valid app locale,
   *  switch + persist it. Without this the only path to a language
   *  switch was the settings page — share-links + smoke-tests + bug
   *  reports all suffered.
   *
   *  Parses with `URL` instead of `ActivatedRoute` because the
   *  router's event firing `NavigationEnd` gives us the full URL
   *  string already, and we don't want to pull in the snapshot
   *  hierarchy here. */
  private applyUrlLangParam(url: string): void {
    const supported = new Set(['en', 'es-MX']);
    const queryStart = url.indexOf('?');
    if (queryStart === -1) return;
    const params = new URLSearchParams(url.slice(queryStart + 1));
    const lang = params.get('lang');
    if (!lang || !supported.has(lang)) return;
    if (this.translocoService.getActiveLang() === lang) return;
    this.translocoService.setActiveLang(lang);
    // Persist via the settings service so the next page-load picks
    // it up. Merge with existing settings rather than overwriting
    // unrelated keys (theme, ai_*).
    const current = (this.settingsService as any)['_settings']?.value || {};
    this.settingsService.saveSettings({
      ai_provider: current.ai_provider ?? '',
      ai_api_key: current.ai_api_key ?? '',
      theme: current.theme ?? 'light',
      language: lang as 'en' | 'es-MX',
    });
  }
}
