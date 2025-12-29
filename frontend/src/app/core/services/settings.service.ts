import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface AppSettings {
  ai_provider: string;
  ai_api_key: string;
  theme: 'light' | 'dark';
}

export interface StoreSettings {
  id?: number;
  settings?: any;
  low_inventory_days_default?: number;
  low_stock_quantity_default?: number;
}

@Injectable({
  providedIn: 'root'
})
export class SettingsService {
  private readonly storageKey = 'fulcrum_settings';
  private apiUrl = `${environment.apiUrl}/inventory-settings`; // Use specific endpoint prefix

  private readonly _settings = new BehaviorSubject<AppSettings | null>(null);
  readonly settings$ = this._settings.asObservable();

  private readonly _storeSettings = new BehaviorSubject<StoreSettings | null>(null);
  readonly storeSettings$ = this._storeSettings.asObservable();

  constructor(private http: HttpClient) {
    this.loadSettings();
    this.loadStoreSettings(); // Load global settings on init
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

  // Store Settings (Backend)

  loadStoreSettings(): void {
    this.http.get<StoreSettings>(`${this.apiUrl}/store`).subscribe({
      next: (settings) => this._storeSettings.next(settings),
      error: (err) => console.error('Failed to load store settings', err)
    });
  }

  getStoreSettings(): Observable<StoreSettings> {
    return this.http.get<StoreSettings>(`${this.apiUrl}/store`).pipe(
      tap(settings => this._storeSettings.next(settings))
    );
  }

  updateStoreSettings(settings: StoreSettings): Observable<StoreSettings> {
    // Backend expects PUT with body matching schema
    return this.http.put<StoreSettings>(`${this.apiUrl}/store`, settings).pipe(
      tap(updated => {
        this._storeSettings.next(updated);
      })
    );
  }
}
