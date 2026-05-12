import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { AuthService } from '../../services/auth.service';
import { User } from '../../../shared/models/user.model';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { SettingsService, AppSettings } from '../../services/settings.service';

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
    MatExpansionModule,
    MatButtonModule,
    MatTooltipModule,
    MatMenuModule,
    MatDividerModule,
    TranslocoModule
  ],
})
export class Sidenav implements OnInit {
  isAdmin$!: Observable<boolean>;
  purchasingExpanded = true;
  marketplacesExpanded = false;
  currentUser$!: Observable<User | null>;
  currentTheme: 'light' | 'dark' = 'light';
  currentLang: 'en' | 'es-MX' = 'en';

  constructor(
    private authService: AuthService,
    private settingsService: SettingsService,
    private translocoService: TranslocoService
  ) { }

  ngOnInit(): void {
    this.isAdmin$ = this.authService.isAdmin();
    this.currentUser$ = this.authService.getCurrentUserObservable();

    this.settingsService.settings$.subscribe(settings => {
      if (settings) {
        this.currentTheme = settings.theme;
        this.currentLang = settings.language;
      }
    });

    // Initialize logic if settings are not loaded yet
    const loaded = this.settingsService.loadSettings();
    if (loaded) {
      this.currentTheme = loaded.theme;
      this.currentLang = loaded.language;
    }
  }

  logout(): void {
    this.authService.logout();
  }

  toggleTheme(): void {
    const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
    const settings = this.settingsService.loadSettings() || { ai_provider: 'openai', ai_api_key: '', theme: 'light', language: 'en' };
    this.settingsService.saveSettings({ ...settings, theme: newTheme });
  }

  setLanguage(lang: 'en' | 'es-MX'): void {
    const settings = this.settingsService.loadSettings() || { ai_provider: 'openai', ai_api_key: '', theme: 'light', language: 'en' };
    // Only save/set if changed
    if (settings.language !== lang) {
      this.settingsService.saveSettings({ ...settings, language: lang });
      this.translocoService.setActiveLang(lang);
    }
  }

  getUserDisplayName(user: User | null): string {
    if (!user) return 'User';
    if (user.first_name && user.last_name) return `${user.first_name} ${user.last_name}`;
    if (user.first_name) return user.first_name;
    if (user.last_name) return user.last_name;
    return user.email?.split('@')[0] || 'User';
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
      case 'admin': return 'Admin';
      case 'employee': return 'Employee';
      case 'customer': return 'Customer';
      default: return user.user_type || 'User';
    }
  }
}
