import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { SettingsService } from '../../../core/services/settings.service';
import { NotificationService } from '../../../core/services/notification.service';
import { CustomFieldList } from '../custom-field-list/custom-field-list';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-settings',
  templateUrl: './settings.html',
  styleUrl: './settings.scss',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule,
    MatIconModule,
    CustomFieldList
  ],
})
export class Settings implements OnInit {
  settingsForm: FormGroup;
  storeSettingsForm: FormGroup;
  smtpForm: FormGroup;

  smtpConfigured = false;
  testingSmtp = false;
  savingSmtp = false;

  private readonly apiUrl = environment.apiUrl;

  constructor(
    private fb: FormBuilder,
    private http: HttpClient,
    private settingsService: SettingsService,
    private notificationService: NotificationService
  ) {
    this.settingsForm = this.fb.group({
      ai_provider: ['', Validators.required],
      ai_api_key: ['', Validators.required],
      theme: ['light', Validators.required]
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
}

