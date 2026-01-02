import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { TranslocoService, TranslocoModule } from '@ngneat/transloco';

import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTabsModule } from '@angular/material/tabs';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { SettingsService } from '../../../core/services/settings.service';
import { NotificationService } from '../../../core/services/notification.service';
import { CustomFieldList } from '../custom-field-list/custom-field-list';
import { environment } from '../../../../environments/environment';
import { IntegrationsService, ApiKeyInfo, ApiKeyCreateResponse } from '../../services/integrations.service';
import { ConfirmationDialog, ConfirmationDialogData } from '../../../shared/components/confirmation-dialog/confirmation-dialog';

@Component({
  selector: 'app-settings',
  templateUrl: './settings.html',
  styleUrl: './settings.scss',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule,
    MatIconModule,
    MatTooltipModule,
    MatTabsModule,
    MatDialogModule,
    TranslocoModule,
  ],
})
export class Settings implements OnInit {
  settingsForm: FormGroup;
  storeSettingsForm: FormGroup;
  smtpForm: FormGroup;

  smtpConfigured = false;
  testingSmtp = false;
  savingSmtp = false;

  // API Keys
  apiKeys: ApiKeyInfo[] = [];
  loadingKeys = false;
  creatingKey = false;
  newKeyName = '';
  newKeyResult: ApiKeyCreateResponse | null = null;

  // Pending Sync
  pendingSyncCount = 0;
  pendingBatchCount = 0;

  private readonly apiUrl = environment.apiUrl;

  constructor(
    private fb: FormBuilder,
    private http: HttpClient,
    private settingsService: SettingsService,
    private notificationService: NotificationService,
    private integrationsService: IntegrationsService,
    private dialog: MatDialog,
    private translocoService: TranslocoService
  ) {
    this.settingsForm = this.fb.group({
      ai_provider: ['', Validators.required],
      ai_api_key: ['', Validators.required],
      theme: ['light', Validators.required],
      language: [this.translocoService.getActiveLang(), Validators.required]
    });

    // Auto-save theme on change
    this.settingsForm.get('theme')?.valueChanges.subscribe(value => {
      // Merge current form values to ensure we don't lose other settings if we were to only save the theme
      const updatedSettings = { ...this.settingsService.loadSettings(), theme: value };
      this.settingsService.saveSettings(updatedSettings as any);
      this.notificationService.showSuccess(`Theme updated to ${value} mode`);
    });

    // Auto-save language on change
    this.settingsForm.get('language')?.valueChanges.subscribe(value => {
      this.translocoService.setActiveLang(value);
      const updatedSettings = { ...this.settingsService.loadSettings(), language: value };
      this.settingsService.saveSettings(updatedSettings as any);
      this.notificationService.showSuccess(value === 'es-MX' ? 'Idioma actualizado a Español' : 'Language updated to English');
    });

    this.storeSettingsForm = this.fb.group({
      low_inventory_days_default: [30, [Validators.required, Validators.min(1)]],
      low_stock_quantity_default: [10, [Validators.required, Validators.min(0)]]
    });

    this.smtpForm = this.fb.group({
      provider: ['gmail'],
      host: [''],
      port: [587],
      username: ['', [Validators.required, Validators.email]],
      password: [''],
      from_name: [''],
    });
  }

  ngOnInit(): void {
    const currentSettings = this.settingsService.loadSettings();
    if (currentSettings) {
      this.settingsForm.patchValue(currentSettings);
    }

    this.settingsService.storeSettings$.subscribe(storeSettings => {
      if (storeSettings) {
        this.storeSettingsForm.patchValue(storeSettings);
      }
    });

    // Load SMTP settings
    this.loadSmtpSettings();

    // Load API Keys
    this.loadApiKeys();

    // Load pending sync count
    this.loadPendingSyncCount();
  }

  onSubmit(): void {
    if (this.settingsForm.valid) {
      this.settingsService.saveSettings(this.settingsForm.value);
      this.notificationService.showSuccess('App Settings saved successfully!');
    }
  }

  onStoreSettingsSubmit(): void {
    if (this.storeSettingsForm.valid) {
      this.settingsService.updateStoreSettings(this.storeSettingsForm.value).subscribe({
        next: () => this.notificationService.showSuccess('Store Settings saved successfully!'),
        error: (err) => this.notificationService.showError('Failed to save store settings')
      });
    }
  }

  // ===============================
  // SMTP Methods
  // ===============================

  loadSmtpSettings(): void {
    this.http.get<any>(`${this.apiUrl}/settings/smtp`).subscribe({
      next: (config) => {
        this.smtpForm.patchValue({
          provider: config.provider || 'gmail',
          host: config.host || '',
          port: config.port || 587,
          username: config.username || '',
          from_name: config.from_name || '',
          // Don't set password - it's never returned
        });
        this.smtpConfigured = config.is_configured;
      },
      error: (err) => console.error('Failed to load SMTP settings', err)
    });
  }

  onProviderChange(provider: string): void {
    // Clear custom fields when switching away from custom
    if (provider !== 'custom') {
      this.smtpForm.patchValue({ host: '', port: 587 });
    }
  }

  onSmtpSubmit(): void {
    if (!this.smtpForm.valid) return;

    this.savingSmtp = true;
    const formValue = this.smtpForm.value;

    this.http.post<any>(`${this.apiUrl}/settings/smtp`, formValue).subscribe({
      next: () => {
        this.savingSmtp = false;
        this.smtpConfigured = true;
        this.notificationService.showSuccess('Email settings saved!');
      },
      error: (err) => {
        this.savingSmtp = false;
        console.error('Failed to save SMTP settings', err);
        this.notificationService.showError('Failed to save email settings');
      }
    });
  }

  testSmtp(): void {
    this.testingSmtp = true;
    this.http.post<any>(`${this.apiUrl}/settings/smtp/test`, {}).subscribe({
      next: (result) => {
        this.testingSmtp = false;
        if (result.success) {
          this.notificationService.showSuccess('SMTP connection successful!');
        } else {
          this.notificationService.showError(result.error || 'Connection failed');
        }
      },
      error: (err) => {
        this.testingSmtp = false;
        this.notificationService.showError('Connection test failed');
      }
    });
  }

  // ===============================
  // API Keys Methods
  // ===============================

  loadApiKeys(): void {
    this.loadingKeys = true;
    this.integrationsService.getApiKeys().subscribe({
      next: (keys) => {
        this.apiKeys = keys;
        this.loadingKeys = false;
      },
      error: (err) => {
        console.error('Failed to load API keys', err);
        this.loadingKeys = false;
      }
    });
  }

  createApiKey(): void {
    if (!this.newKeyName) return;

    this.creatingKey = true;
    this.integrationsService.createApiKey(this.newKeyName).subscribe({
      next: (result) => {
        this.newKeyResult = result;
        this.creatingKey = false;
        this.newKeyName = '';
        this.loadApiKeys(); // Refresh list
      },
      error: (err) => {
        console.error('Failed to create API key', err);
        this.notificationService.showError('Failed to create API key');
        this.creatingKey = false;
      }
    });
  }

  revokeKey(keyId: number): void {
    const dialogRef = this.dialog.open(ConfirmationDialog, {
      data: {
        title: 'Revoke API Key',
        message: 'Are you sure you want to revoke this API key? This cannot be undone.'
      } as ConfirmationDialogData
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (!confirmed) return;

      this.integrationsService.revokeApiKey(keyId).subscribe({
        next: () => {
          this.notificationService.showSuccess('API key revoked');
          this.loadApiKeys();
        },
        error: (err) => {
          this.notificationService.showError('Failed to revoke API key');
        }
      });
    });
  }

  dismissKeyResult(): void {
    this.newKeyResult = null;
  }

  // ===============================
  // API Key Visibility & Deletion
  // ===============================
  showRevokedKeys = false;

  getVisibleKeys(): ApiKeyInfo[] {
    if (this.showRevokedKeys) {
      return this.apiKeys;
    }
    return this.apiKeys.filter(k => k.is_active);
  }

  hasRevokedKeys(): boolean {
    return this.apiKeys.some(k => !k.is_active);
  }

  getRevokedCount(): number {
    return this.apiKeys.filter(k => !k.is_active).length;
  }

  deleteRevokedKey(keyId: number): void {
    const dialogRef = this.dialog.open(ConfirmationDialog, {
      data: {
        title: 'Delete Revoked Key',
        message: 'Permanently delete this revoked key from history?'
      } as ConfirmationDialogData
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (!confirmed) return;

      // For now, just remove from local list (backend can add permanent delete endpoint later)
      this.apiKeys = this.apiKeys.filter(k => k.id !== keyId);
      this.notificationService.showSuccess('Key removed from list');
    });
  }

  copyToClipboard(text: string): void {
    navigator.clipboard.writeText(text).then(() => {
      this.notificationService.showSuccess('Copied to clipboard!');
    });
  }

  // ===============================
  // Data Export Methods
  // ===============================

  exportData(entity: string, format: 'csv' | 'json'): void {
    const filename = `${entity.replace('-', '_')}_export.${format}`;

    this.integrationsService.exportEntity(entity, format).subscribe({
      next: (blob) => {
        this.integrationsService.downloadBlob(blob, filename);
        this.notificationService.showSuccess(`${entity.replace('-', ' ')} exported successfully!`);
      },
      error: (err) => {
        console.error('Export failed', err);
        this.notificationService.showError('Export failed. Please try again.');
      }
    });
  }

  // ===============================
  // Pending Sync Methods
  // ===============================

  loadPendingSyncCount(): void {
    this.integrationsService.getPendingSyncCount().subscribe({
      next: (response) => {
        this.pendingSyncCount = response.count;
        this.pendingBatchCount = response.batch_count;
      },
      error: (err) => {
        console.error('Failed to load pending sync count', err);
      }
    });
  }

  openPendingSyncDialog(): void {
    import('../pending-sync-dialog/pending-sync-dialog').then(m => {
      const dialogRef = this.dialog.open(m.PendingSyncDialog, {
        width: '90vw',
        maxWidth: '900px',
        maxHeight: '90vh',
        panelClass: 'pending-sync-dialog'
      });

      dialogRef.afterClosed().subscribe(() => {
        // Refresh count after dialog closes
        this.loadPendingSyncCount();
      });
    });
  }

  openChangeLogDialog(): void {
    import('../change-log-dialog/change-log-dialog').then(m => {
      this.dialog.open(m.ChangeLogDialog, {
        width: '90vw',
        maxWidth: '1000px',
        maxHeight: '90vh',
        panelClass: 'change-log-dialog'
      });
    });
  }
}
