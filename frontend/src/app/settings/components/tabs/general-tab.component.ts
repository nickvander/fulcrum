import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { MaterialModule } from '../../../shared/material.module';
import { SettingsService } from '../../../core/services/settings.service';
import { NotificationService } from '../../../core/services/notification.service';

@Component({
  selector: 'app-general-tab',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, TranslocoModule, MaterialModule],
  templateUrl: './general-tab.component.html',
  styleUrls: ['./general-tab.component.scss']
})
export class GeneralTabComponent implements OnInit {
  form: FormGroup;

  constructor(
    private fb: FormBuilder,
    private settingsService: SettingsService,
    private translocoService: TranslocoService,
    private notificationService: NotificationService
  ) {
    this.form = this.fb.group({
      theme: ['light', Validators.required],
      language: [this.translocoService.getActiveLang(), Validators.required]
    });
  }

  ngOnInit(): void {
    const currentSettings = this.settingsService.loadSettings();
    if (currentSettings) {
      this.form.patchValue({
        theme: currentSettings.theme || 'light',
        language: currentSettings.language || this.translocoService.getActiveLang()
      }, { emitEvent: false });
    }

    // Auto-save theme on change
    this.form.get('theme')?.valueChanges.subscribe(value => {
      const updatedSettings = { ...this.settingsService.loadSettings(), theme: value };
      this.settingsService.saveSettings(updatedSettings as any);
    });

    // Auto-save language on change
    this.form.get('language')?.valueChanges.subscribe(value => {
      this.translocoService.setActiveLang(value);
      const updatedSettings = { ...this.settingsService.loadSettings(), language: value };
      this.settingsService.saveSettings(updatedSettings as any);
    });
  }
}
