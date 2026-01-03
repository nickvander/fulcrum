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
import { TranslocoModule } from '@ngneat/transloco';

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
    TranslocoModule,
  ],
  templateUrl: './connector-settings.component.html',
  styleUrls: ['./connector-settings.component.scss']
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
