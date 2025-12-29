import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';

import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { SettingsService } from '../../../core/services/settings.service';
import { NotificationService } from '../../../core/services/notification.service';
import { CustomFieldList } from '../custom-field-list/custom-field-list';

@Component({
  selector: 'app-settings',
  templateUrl: './settings.html',
  styleUrl: './settings.scss',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule,
    CustomFieldList
  ],
})
export class Settings implements OnInit {
  settingsForm: FormGroup;
  storeSettingsForm: FormGroup;

  constructor(
    private fb: FormBuilder,
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
}
