import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, FormsModule, Validators } from '@angular/forms';
import { MatDialog } from '@angular/material/dialog';
import { TranslocoModule } from '@ngneat/transloco';
import { MaterialModule } from '../../../shared/material.module';
import { IntegrationsService, ApiKeyInfo, ApiKeyCreateResponse } from '../../services/integrations.service';
import { NotificationService } from '../../../core/services/notification.service';
import { ConfirmationDialog, ConfirmationDialogData } from '../../../shared/components/confirmation-dialog/confirmation-dialog';
import { SettingsService } from '../../../core/services/settings.service';

@Component({
  selector: 'app-integrations-tab',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule, TranslocoModule, MaterialModule],
  templateUrl: './integrations-tab.component.html',
  styleUrls: ['./integrations-tab.component.scss']
})
export class IntegrationsTabComponent implements OnInit {
  aiForm: FormGroup;
  apiKeys: ApiKeyInfo[] = [];
  loadingKeys = false;
  creatingKey = false;
  newKeyName = '';
  newKeyResult: ApiKeyCreateResponse | null = null;
  showRevokedKeys = false;
  pendingSyncCount = 0;
  pendingBatchCount = 0;

  constructor(
    private fb: FormBuilder,
    private integrationsService: IntegrationsService,
    private notificationService: NotificationService,
    private settingsService: SettingsService,
    private dialog: MatDialog
  ) {
    this.aiForm = this.fb.group({
      ai_provider: ['', Validators.required],
      ai_api_key: ['', Validators.required]
    });
  }

  ngOnInit(): void {
    const currentSettings = this.settingsService.loadSettings();
    if (currentSettings) {
      this.aiForm.patchValue(currentSettings);
    }
    this.loadApiKeys();
    this.loadPendingSyncCount();
  }

  onAiSubmit(): void {
    if (this.aiForm.valid) {
      this.settingsService.saveSettings(this.aiForm.value);
      this.notificationService.showSuccess('AI Settings saved successfully!');
    }
  }

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
        this.loadApiKeys();
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

  deleteRevokedKey(keyId: number): void {
    const dialogRef = this.dialog.open(ConfirmationDialog, {
      data: {
        title: 'Delete Revoked Key',
        message: 'Permanently delete this revoked key from history?'
      } as ConfirmationDialogData
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.apiKeys = this.apiKeys.filter(k => k.id !== keyId);
        this.notificationService.showSuccess('Key removed from list');
      }
    });
  }

  dismissKeyResult(): void { this.newKeyResult = null; }

  copyToClipboard(text: string): void {
    navigator.clipboard.writeText(text).then(() => {
      this.notificationService.showSuccess('Copied to clipboard!');
    });
  }

  getVisibleKeys(): ApiKeyInfo[] {
    return this.showRevokedKeys ? this.apiKeys : this.apiKeys.filter(k => k.is_active);
  }

  hasRevokedKeys(): boolean { return this.apiKeys.some(k => !k.is_active); }
  getRevokedCount(): number { return this.apiKeys.filter(k => !k.is_active).length; }

  loadPendingSyncCount(): void {
    this.integrationsService.getPendingSyncCount().subscribe({
      next: (response) => {
        this.pendingSyncCount = response.count;
        this.pendingBatchCount = response.batch_count;
      },
      error: (err) => { console.error('Failed to load pending sync count', err); }
    });
  }

  openPendingSyncDialog(): void {
    import('../pending-sync-dialog/pending-sync-dialog').then(m => {
      const dialogRef = this.dialog.open(m.PendingSyncDialog, {
        width: '90vw', maxWidth: '900px', maxHeight: '90vh', panelClass: 'pending-sync-dialog'
      });
      dialogRef.afterClosed().subscribe(() => { this.loadPendingSyncCount(); });
    });
  }

  openChangeLogDialog(): void {
    import('../change-log-dialog/change-log-dialog').then(m => {
      this.dialog.open(m.ChangeLogDialog, {
        width: '90vw', maxWidth: '1000px', maxHeight: '90vh', panelClass: 'change-log-dialog'
      });
    });
  }
}
