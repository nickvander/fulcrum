import { Component, OnInit, OnDestroy, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { Observable, Subscription, filter } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { User } from '../../../shared/models/user.model';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { SettingsService } from '../../services/settings.service';

/**
 * Stable ids for the collapsible nav groups. Used to key the route-derived
 * auto-expand state + remembered manual toggles (replaces the old hardcoded
 * purchasingExpanded / marketplacesExpanded booleans).
 */
type NavGroupId = 'purchasing' | 'marketplaces' | 'inventory';

interface NavGroupDef {
  id: NavGroupId;
  /** Child routes that, when active, force the group open. */
  routes: string[];
}

const EXPAND_KEY = 'fulcrum_sidenav_expanded';

@Component({
  selector: 'app-sidenav',
  templateUrl: './sidenav.html',
  styleUrls: ['./sidenav.scss'],
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatMenuModule,
    MatDividerModule,
    TranslocoModule,
  ],
})
export class Sidenav implements OnInit, OnDestroy {
  /** Desktop rail collapsed (icon-only, 76px) vs full (248px). */
  @Input() collapsed = false;

  isAdmin$!: Observable<boolean>;
  currentUser$!: Observable<User | null>;
  currentTheme: 'light' | 'dark' = SettingsService.DEFAULT_SETTINGS.theme;
  currentLang: 'en' | 'es-MX' = SettingsService.DEFAULT_SETTINGS.language;

  /** Per-group open/closed state, keyed by group id. */
  expanded: Record<NavGroupId, boolean> = {
    purchasing: false,
    marketplaces: false,
    inventory: false,
  };

  private readonly groups: NavGroupDef[] = [
    { id: 'inventory', routes: ['/products', '/products/audit', '/inventory/count'] },
    { id: 'purchasing', routes: ['/suppliers', '/suppliers/po'] },
    {
      id: 'marketplaces',
      routes: ['/marketplaces', '/marketplaces/health'],
    },
  ];

  private manual: Partial<Record<NavGroupId, boolean>> = {};
  private routerSub?: Subscription;

  constructor(
    private authService: AuthService,
    private settingsService: SettingsService,
    private translocoService: TranslocoService,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.isAdmin$ = this.authService.isAdmin();
    this.currentUser$ = this.authService.getCurrentUserObservable();

    this.settingsService.settings$.subscribe(settings => {
      if (settings) {
        this.currentTheme = settings.theme;
        this.currentLang = settings.language;
      }
    });

    const loaded = this.settingsService.loadSettings();
    if (loaded) {
      this.currentTheme = loaded.theme;
      this.currentLang = loaded.language;
    }

    // Route-derived auto-expand: the group owning the active route opens
    // automatically; manual toggles are remembered for the rest.
    this.manual = this.loadManual();
    this.syncFromRoute(this.router.url);
    this.routerSub = this.router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe(e => this.syncFromRoute(e.urlAfterRedirects));
  }

  ngOnDestroy(): void {
    this.routerSub?.unsubscribe();
  }

  private syncFromRoute(url: string): void {
    for (const group of this.groups) {
      const routeMatch = group.routes.some(r => this.isActive(url, r));
      // Active route always wins (force open). Otherwise honor a manual toggle.
      this.expanded[group.id] = routeMatch
        ? true
        : this.manual[group.id] ?? false;
    }
  }

  toggleGroup(id: NavGroupId): void {
    const next = !this.expanded[id];
    this.expanded[id] = next;
    this.manual[id] = next;
    this.saveManual();
  }

  groupHasActiveChild(id: NavGroupId): boolean {
    const group = this.groups.find(g => g.id === id);
    return !!group?.routes.some(r => this.isActive(this.router.url, r));
  }

  private isActive(url: string, route: string): boolean {
    const clean = url.split('?')[0].split('#')[0];
    return clean === route || clean.startsWith(route + '/');
  }

  private loadManual(): Partial<Record<NavGroupId, boolean>> {
    try {
      const raw = localStorage.getItem(EXPAND_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  }

  private saveManual(): void {
    try {
      localStorage.setItem(EXPAND_KEY, JSON.stringify(this.manual));
    } catch {
      /* storage unavailable; ignore */
    }
  }

  logout(): void {
    this.authService.logout();
  }

  toggleTheme(): void {
    const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
    const settings = this.settingsService.loadSettings() ?? { ...SettingsService.DEFAULT_SETTINGS };
    this.settingsService.saveSettings({ ...settings, theme: newTheme });
  }

  setLanguage(lang: 'en' | 'es-MX'): void {
    const settings = this.settingsService.loadSettings() ?? { ...SettingsService.DEFAULT_SETTINGS };
    if (settings.language !== lang) {
      this.settingsService.saveSettings({ ...settings, language: lang });
      this.translocoService.setActiveLang(lang);
    }
  }

  getUserDisplayName(user: User | null): string {
    const fallback = this.translocoService.translate('core.sidenav.userFallbackName');
    if (!user) return fallback;
    if (user.first_name && user.last_name) return `${user.first_name} ${user.last_name}`;
    if (user.first_name) return user.first_name;
    if (user.last_name) return user.last_name;
    return user.email?.split('@')[0] || fallback;
  }

  getUserInitials(user: User | null): string {
    if (!user) return 'U';
    const name = this.getUserDisplayName(user);
    const parts = name.split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  }

  getUserRole(user: User | null): string {
    if (!user) return '';
    switch (user.user_type) {
      case 'admin': return this.translocoService.translate('core.sidenav.roles.admin');
      case 'employee': return this.translocoService.translate('core.sidenav.roles.employee');
      case 'customer': return this.translocoService.translate('core.sidenav.roles.customer');
      default: return user.user_type || this.translocoService.translate('core.sidenav.roles.user');
    }
  }
}
