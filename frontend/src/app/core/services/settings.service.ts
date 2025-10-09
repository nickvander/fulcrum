import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface AppSettings {
  ai_provider: string;
  ai_api_key: string;
  theme: 'light' | 'dark';
}

@Injectable({
  providedIn: 'root'
})
export class SettingsService {
  private readonly storageKey = 'fulcrum_settings';
  private readonly _settings = new BehaviorSubject<AppSettings | null>(null);
  readonly settings$ = this._settings.asObservable();

  constructor() {
    this.loadSettings();
  }

  loadSettings(): AppSettings | null {
    try {
      const settingsStr = localStorage.getItem(this.storageKey);
      if (settingsStr) {
        const settings = JSON.parse(settingsStr);
        this._settings.next(settings);
        return settings;
      }
    } catch (e) {
      console.error('Error loading settings from localStorage', e);
    }
    return null;
  }

  saveSettings(settings: AppSettings): void {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(settings));
      this._settings.next(settings);
    } catch (e) {
      console.error('Error saving settings to localStorage', e);
    }
  }
}
