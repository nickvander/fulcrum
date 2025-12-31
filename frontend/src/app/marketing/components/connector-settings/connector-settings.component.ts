import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { RouterModule } from '@angular/router';

import {
  MarketingService,
  MarketingConnector,
  ConnectorCreate,
  EMAIL_PROVIDER_PRESETS
} from '../../services/marketing.service';
import { ConfirmationDialog, ConfirmationDialogData } from '../../../shared/components/confirmation-dialog/confirmation-dialog';

@Component({
  selector: 'app-connector-settings',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatDialogModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatChipsModule,
  ],
  template: `
    <div class="connector-settings-container">
      <div class="page-header">
        <div class="header-content">
          <button mat-icon-button routerLink="/marketing">
            <mat-icon>arrow_back</mat-icon>
          </button>
          <div>
            <h1>Marketing Connectors</h1>
            <p class="subtitle">Connect your email, social, and ad platforms</p>
          </div>
        </div>
      </div>

      <!-- Connector Categories -->
      <div class="connector-categories">
        <!-- Email Connectors -->
        <mat-card class="category-card">
          <mat-card-header>
            <mat-icon mat-card-avatar>email</mat-icon>
            <mat-card-title>Email Marketing</mat-card-title>
            <mat-card-subtitle>Send newsletters and promotional emails</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content>
            <div class="provider-grid">
              <div class="provider-option" *ngFor="let provider of emailProviders"
                   (click)="openEmailSetup(provider.key)">
                <div class="provider-icon" [ngClass]="provider.key">
                  <mat-icon>{{ provider.icon }}</mat-icon>
                </div>
                <span>{{ provider.name }}</span>
                <mat-chip *ngIf="hasConnector('smtp', provider.key)" color="primary" selected>
                  Connected
                </mat-chip>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <!-- Social Connectors -->
        <mat-card class="category-card">
          <mat-card-header>
            <mat-icon mat-card-avatar>share</mat-icon>
            <mat-card-title>Social Media</mat-card-title>
            <mat-card-subtitle>Post to Instagram, Facebook, TikTok, and more</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content>
            <div class="provider-grid">
              <div class="provider-option" *ngFor="let provider of socialProviders"
                   (click)="openSocialSetup(provider.key)">
                <div class="provider-icon" [ngClass]="provider.key">
                  <mat-icon>{{ provider.icon }}</mat-icon>
                </div>
                <span>{{ provider.name }}</span>
                <mat-chip *ngIf="hasConnector(provider.key)" color="primary" selected>
                  Connected
                </mat-chip>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <!-- Ad Connectors -->
        <mat-card class="category-card">
          <mat-card-header>
            <mat-icon mat-card-avatar>trending_up</mat-icon>
            <mat-card-title>Paid Advertising</mat-card-title>
            <mat-card-subtitle>Connect Google Ads, Meta Ads, and more</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content>
            <div class="provider-grid">
              <div class="provider-option coming-soon" *ngFor="let provider of adProviders">
                <div class="provider-icon" [ngClass]="provider.key">
                  <mat-icon>{{ provider.icon }}</mat-icon>
                </div>
                <span>{{ provider.name }}</span>
                <mat-chip>Coming Soon</mat-chip>
              </div>
            </div>
          </mat-card-content>
        </mat-card>
      </div>

      <!-- Active Connectors -->
      <mat-card class="active-connectors-card" *ngIf="connectors.length > 0">
        <mat-card-header>
          <mat-card-title>Active Connectors</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <div class="connector-list">
            <div class="connector-item" *ngFor="let connector of connectors">
              <div class="connector-info">
                <mat-icon>{{ getConnectorIcon(connector.connector_type) }}</mat-icon>
                <div>
                  <strong>{{ connector.name }}</strong>
                  <small>{{ connector.connector_type | titlecase }} • {{ connector.channel_type | titlecase }}</small>
                </div>
              </div>
              <div class="connector-actions">
                <mat-slide-toggle [checked]="connector.is_active" 
                                  (change)="toggleConnector(connector, $event.checked)">
                </mat-slide-toggle>
                <button mat-icon-button (click)="testConnector(connector)" [disabled]="testing === connector.id">
                  <mat-spinner diameter="20" *ngIf="testing === connector.id"></mat-spinner>
                  <mat-icon *ngIf="testing !== connector.id">sync</mat-icon>
                </button>
                <button mat-icon-button color="warn" (click)="deleteConnector(connector)">
                  <mat-icon>delete</mat-icon>
                </button>
              </div>
            </div>
          </div>
        </mat-card-content>
      </mat-card>

      <!-- Email Setup Dialog -->
      <div class="setup-overlay" *ngIf="showEmailSetup" (click)="closeEmailSetup()">
        <mat-card class="setup-dialog" (click)="$event.stopPropagation()">
          <mat-card-header>
            <mat-card-title>Set Up Email Marketing</mat-card-title>
            <button mat-icon-button (click)="closeEmailSetup()">
              <mat-icon>close</mat-icon>
            </button>
          </mat-card-header>
          <mat-card-content>
            <form [formGroup]="emailForm">
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Email Provider</mat-label>
                <mat-select formControlName="provider" (selectionChange)="onProviderChange($event.value)">
                  <mat-option value="gmail">Gmail</mat-option>
                  <mat-option value="outlook">Outlook</mat-option>
                  <mat-option value="yahoo">Yahoo</mat-option>
                  <mat-option value="custom">Custom SMTP</mat-option>
                </mat-select>
              </mat-form-field>

              <p class="help-text" *ngIf="selectedProvider?.help_text">
                {{ selectedProvider.help_text }}
              </p>

              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Connection Name</mat-label>
                <input matInput formControlName="name" placeholder="e.g., My Gmail">
              </mat-form-field>

              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Email Address</mat-label>
                <input matInput formControlName="username" type="email" placeholder="you@gmail.com">
              </mat-form-field>

              <mat-form-field appearance="outline" class="full-width">
                <mat-label>App Password</mat-label>
                <input matInput formControlName="password" type="password" placeholder="••••••••">
                <mat-hint>Use an app-specific password, not your regular password</mat-hint>
              </mat-form-field>

              <!-- Custom SMTP fields -->
              <div *ngIf="selectedProviderKey === 'custom'" class="custom-smtp-fields">
                <mat-form-field appearance="outline">
                  <mat-label>SMTP Host</mat-label>
                  <input matInput formControlName="host" placeholder="smtp.example.com">
                </mat-form-field>

                <mat-form-field appearance="outline">
                  <mat-label>Port</mat-label>
                  <input matInput formControlName="port" type="number" placeholder="587">
                </mat-form-field>
              </div>
            </form>
          </mat-card-content>
          <mat-card-actions>
            <button mat-stroked-button (click)="closeEmailSetup()">Cancel</button>
            <button mat-raised-button color="primary" (click)="saveEmailConnector()" 
                    [disabled]="emailForm.invalid || saving">
              <mat-spinner diameter="20" *ngIf="saving"></mat-spinner>
              <span *ngIf="!saving">Connect</span>
            </button>
          </mat-card-actions>
        </mat-card>
      </div>

      <!-- Social Setup Dialog -->
      <div class="setup-overlay" *ngIf="showSocialSetup" (click)="closeSocialSetup()">
        <mat-card class="setup-dialog" (click)="$event.stopPropagation()">
          <mat-card-header>
            <mat-card-title>Set Up {{ selectedProviderKey | titlecase }}</mat-card-title>
            <button mat-icon-button (click)="closeSocialSetup()">
              <mat-icon>close</mat-icon>
            </button>
          </mat-card-header>
          <mat-card-content>
            <p class="help-text">
              Enter your access token or API key to connect your account.
            </p>

            <form [formGroup]="socialForm">
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Connection Name</mat-label>
                <input matInput formControlName="name" placeholder="e.g., Brand Instagram">
              </mat-form-field>

              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Access Token / API Key</mat-label>
                <input matInput formControlName="api_key" type="password" placeholder="••••••••">
              </mat-form-field>
            </form>
          </mat-card-content>
          <mat-card-actions>
            <button mat-stroked-button (click)="closeSocialSetup()">Cancel</button>
            <button mat-raised-button color="primary" (click)="saveSocialConnector()" 
                    [disabled]="socialForm.invalid || saving">
              <mat-spinner diameter="20" *ngIf="saving"></mat-spinner>
              <span *ngIf="!saving">Connect</span>
            </button>
          </mat-card-actions>
        </mat-card>
      </div>
    </div>

  `,
  styles: [`
    .connector-settings-container {
      padding: 24px;
      max-width: 1000px;
      margin: 0 auto;
    }

    .page-header {
      margin-bottom: 24px;
    }

    .header-content {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .header-content h1 {
      margin: 0;
      font-size: 24px;
    }

    .subtitle {
      margin: 0;
      color: #666;
    }

    .category-card {
      margin-bottom: 24px;
      border-radius: 12px;
    }

    mat-card-header mat-icon[mat-card-avatar] {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 8px;
      border-radius: 8px;
    }

    .provider-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 16px;
      padding: 16px 0;
    }

    .provider-option {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px;
      border: 2px solid #e0e0e0;
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.2s;
      gap: 8px;
    }

    .provider-option:hover:not(.coming-soon) {
      border-color: #1976d2;
      background: #e3f2fd;
    }

    .provider-option.coming-soon {
      opacity: 0.6;
      cursor: not-allowed;
    }

    .provider-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #f5f5f5;
    }

    .provider-icon.gmail { background: #ea4335; color: white; }
    .provider-icon.outlook { background: #0078d4; color: white; }
    .provider-icon.yahoo { background: #6001d2; color: white; }
    .provider-icon.custom { background: #424242; color: white; }
    .provider-icon.instagram { background: linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888); color: white; }
    .provider-icon.facebook { background: #1877f2; color: white; }
    .provider-icon.tiktok { background: #000; color: white; }
    .provider-icon.google_ads { background: #4285f4; color: white; }
    .provider-icon.meta_ads { background: #0081fb; color: white; }

    .connector-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .connector-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      background: #f5f5f5;
      border-radius: 8px;
    }

    .connector-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .connector-info small {
      display: block;
      color: #666;
    }

    .connector-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .setup-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0,0,0,0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }

    .setup-dialog {
      width: 100%;
      max-width: 480px;
      border-radius: 12px;
    }

    .setup-dialog mat-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .setup-dialog mat-card-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      padding: 16px;
    }

    .full-width {
      width: 100%;
    }

    .help-text {
      background: #fff3e0;
      padding: 12px;
      border-radius: 8px;
      margin-bottom: 16px;
      color: #e65100;
    }

    .custom-smtp-fields {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 16px;
    }
  `]
})
export class ConnectorSettingsComponent implements OnInit {
  connectors: MarketingConnector[] = [];
  loading = true;
  saving = false;
  testing: number | null = null;

  showEmailSetup = false;
  showSocialSetup = false;
  selectedProviderKey = '';
  selectedProvider: any = null;

  emailForm: FormGroup;
  socialForm: FormGroup;

  emailProviders = [
    { key: 'email', name: 'Email Marketing', icon: 'mail' },
  ];

  socialProviders = [
    { key: 'instagram', name: 'Instagram', icon: 'camera_alt' },
    { key: 'facebook', name: 'Facebook', icon: 'thumb_up' },
    { key: 'tiktok', name: 'TikTok', icon: 'play_circle' },
    { key: 'twitter', name: 'Twitter', icon: 'chat' },
  ];

  adProviders = [
    { key: 'google_ads', name: 'Google Ads', icon: 'ads_click' },
    { key: 'meta_ads', name: 'Meta Ads', icon: 'campaign' },
  ];

  constructor(
    private fb: FormBuilder,
    private marketingService: MarketingService,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
  ) {
    this.emailForm = this.fb.group({
      provider: ['gmail', Validators.required],
      name: ['', Validators.required],
      username: ['', [Validators.required, Validators.email]],
      password: ['', Validators.required],
      host: [''],
      port: [587],
    });

    this.socialForm = this.fb.group({
      name: ['', Validators.required],
      api_key: ['', Validators.required],
    });
  }

  ngOnInit(): void {
    this.loadConnectors();
  }

  loadConnectors(): void {
    this.marketingService.getConnectors(false).subscribe({
      next: (connectors) => {
        this.connectors = connectors;
        this.loading = false;
      },
      error: (err) => {
        console.error('Failed to load connectors', err);
        this.loading = false;
      }
    });
  }

  hasConnector(typeOrKey: string, provider?: string): boolean {
    if (provider) {
      return this.connectors.some(c =>
        c.connector_type === typeOrKey && c.config_json?.provider === provider
      );
    }
    return this.connectors.some(c => c.connector_type === typeOrKey);
  }

  getConnectorIcon(type: string): string {
    const icons: Record<string, string> = {
      smtp: 'email',
      instagram: 'camera_alt',
      facebook: 'thumb_up',
      tiktok: 'play_circle',
      twitter: 'chat',
      whatsapp: 'chat',
      google_ads: 'ads_click',
    };
    return icons[type] || 'extension';
  }

  openEmailSetup(key: string): void {
    // key is 'email' here usually
    this.emailForm.reset({
      provider: 'gmail',
      name: 'My Email Marketing',
      port: 587,
    });
    this.onProviderChange('gmail');
    this.showEmailSetup = true;
  }

  onProviderChange(providerKey: string): void {
    this.selectedProvider = EMAIL_PROVIDER_PRESETS[providerKey as keyof typeof EMAIL_PROVIDER_PRESETS];
    if (providerKey !== 'custom' && this.selectedProvider) {
      this.emailForm.patchValue({
        host: this.selectedProvider.host,
        port: this.selectedProvider.port,
      });
    }
    // Update selectedProviderKey for template usage if needed (e.g. for custom fields visibility)
    this.selectedProviderKey = providerKey;
  }

  closeEmailSetup(): void {
    this.showEmailSetup = false;
    this.selectedProviderKey = '';
    this.selectedProvider = null;
  }

  openSocialSetup(provider: string): void {
    this.selectedProviderKey = provider;
    this.socialForm.reset({
      name: `My ${provider.charAt(0).toUpperCase() + provider.slice(1)}`
    });
    this.showSocialSetup = true;
  }

  closeSocialSetup(): void {
    this.showSocialSetup = false;
    this.selectedProviderKey = '';
  }

  saveEmailConnector(): void {
    if (this.emailForm.invalid) return;

    this.saving = true;
    const formValue = this.emailForm.value;
    const providerKey = formValue.provider;
    const preset = EMAIL_PROVIDER_PRESETS[providerKey as keyof typeof EMAIL_PROVIDER_PRESETS] || {};

    const connector: ConnectorCreate = {
      name: formValue.name,
      connector_type: 'smtp',
      channel_type: 'email',
      config_json: {
        provider: providerKey,
        host: formValue.host || (preset as any).host,
        port: formValue.port || (preset as any).port || 587,
        use_tls: (preset as any).use_tls ?? true,
        use_ssl: (preset as any).use_ssl ?? false,
        username: formValue.username,
        from_email: formValue.username,
      },
      api_key: formValue.username,
      api_secret: formValue.password,
    };

    this.createConnector(connector, () => this.closeEmailSetup());
  }

  saveSocialConnector(): void {
    if (this.socialForm.invalid) return;

    this.saving = true;
    const formValue = this.socialForm.value;

    const connector: ConnectorCreate = {
      name: formValue.name,
      connector_type: this.selectedProviderKey,
      channel_type: 'social',
      config_json: { simulation_mode: true },
      api_key: formValue.api_key,
    };

    this.createConnector(connector, () => this.closeSocialSetup());
  }

  createConnector(connector: ConnectorCreate, onSuccess: () => void): void {
    this.marketingService.createConnector(connector).subscribe({
      next: (created) => {
        this.saving = false;
        this.connectors.push(created);
        onSuccess();
        this.snackBar.open('Connector created!', 'Close', { duration: 3000 });
      },
      error: (err) => {
        this.saving = false;
        console.error('Failed to create connector', err);
        this.snackBar.open('Failed to create connector', 'Close', { duration: 3000 });
      }
    });
  }

  toggleConnector(connector: MarketingConnector, active: boolean): void {
    this.marketingService.updateConnector(connector.id, { is_active: active }).subscribe({
      next: (updated) => {
        connector.is_active = updated.is_active;
      },
      error: (err) => console.error('Failed to update connector', err)
    });
  }

  testConnector(connector: MarketingConnector): void {
    this.testing = connector.id;
    this.marketingService.testConnector(connector.id).subscribe({
      next: (result) => {
        this.testing = null;
        if (result.valid) {
          this.snackBar.open('Connection successful!', 'Close', { duration: 3000 });
        } else {
          this.snackBar.open('Connection failed. Check credentials.', 'Close', { duration: 3000 });
        }
      },
      error: (err) => {
        this.testing = null;
        this.snackBar.open('Connection test failed', 'Close', { duration: 3000 });
      }
    });
  }

  deleteConnector(connector: MarketingConnector): void {
    const dialogRef = this.dialog.open(ConfirmationDialog, {
      data: {
        title: 'Delete Connector',
        message: `Delete "${connector.name}"?`
      } as ConfirmationDialogData
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.marketingService.deleteConnector(connector.id).subscribe({
          next: () => {
            this.connectors = this.connectors.filter(c => c.id !== connector.id);
            this.snackBar.open('Connector deleted', 'Close', { duration: 2000 });
          },
          error: (err) => {
            console.error('Failed to delete connector', err);
            this.snackBar.open('Failed to delete connector', 'Close', { duration: 3000 });
          }
        });
      }
    });
  }
}
