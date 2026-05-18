import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';

import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { TranslocoModule } from '@ngneat/transloco';

import {
  AlertRule,
  AlertRuleCreate,
  AlertRuleUpdate,
  AlertType,
} from '../../services/alerts.service';

export interface AlertFormDialogData {
  mode: 'create' | 'edit';
  rule?: AlertRule;
}

export interface AlertFormDialogResult {
  mode: 'create' | 'edit';
  payload: AlertRuleCreate | AlertRuleUpdate;
}

/**
 * Create / edit dialog for a single AlertRule. The `mode` from the
 * dialog data drives whether `alert_type` is a select (create) or
 * read-only label (edit — changing type is forbidden because the
 * threshold's units change with it).
 */
@Component({
  selector: 'app-alert-form-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
    TranslocoModule,
  ],
  templateUrl: './alert-form-dialog.component.html',
  styleUrls: ['./alert-form-dialog.component.scss'],
})
export class AlertFormDialogComponent {
  form: FormGroup;
  alertTypes: AlertType[] = ['low_margin', 'sales_dip', 'stockout_risk'];

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<AlertFormDialogComponent, AlertFormDialogResult | null>,
    @Inject(MAT_DIALOG_DATA) public data: AlertFormDialogData,
  ) {
    const rule = data.rule;
    this.form = this.fb.group({
      alert_type: [
        { value: rule?.alert_type ?? 'low_margin', disabled: data.mode === 'edit' },
        Validators.required,
      ],
      threshold: [rule?.threshold ?? 50, [Validators.required, Validators.min(0)]],
      window_days: [rule?.window_days ?? 30, [Validators.required, Validators.min(1), Validators.max(365)]],
      cooldown_minutes: [
        rule?.cooldown_minutes ?? 720,
        [Validators.required, Validators.min(5), Validators.max(60 * 24 * 30)],
      ],
      notify_email: [
        rule?.notify_email ?? '',
        [Validators.required, Validators.email],
      ],
      enabled: [rule?.enabled ?? true],
    });
  }

  /** Threshold label changes per type — the value's units (% / count)
   *  are different, so the form needs to explain itself. */
  thresholdHintKey(): string {
    const t = this.form.get('alert_type')?.value as AlertType;
    if (t === 'low_margin') return 'alerts.form.thresholdHintLowMargin';
    if (t === 'sales_dip') return 'alerts.form.thresholdHintSalesDip';
    return 'alerts.form.thresholdHintStockoutRisk';
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const raw = this.form.getRawValue();
    if (this.data.mode === 'create') {
      const payload: AlertRuleCreate = {
        alert_type: raw.alert_type,
        threshold: raw.threshold,
        window_days: raw.window_days,
        cooldown_minutes: raw.cooldown_minutes,
        notify_email: raw.notify_email,
        enabled: raw.enabled,
      };
      this.dialogRef.close({ mode: 'create', payload });
    } else {
      // Edit mode: omit alert_type (disabled). Send only the editable
      // fields — the API supports partial PATCH but sending everything
      // is fine since they're all the user's values.
      const payload: AlertRuleUpdate = {
        threshold: raw.threshold,
        window_days: raw.window_days,
        cooldown_minutes: raw.cooldown_minutes,
        notify_email: raw.notify_email,
        enabled: raw.enabled,
      };
      this.dialogRef.close({ mode: 'edit', payload });
    }
  }

  cancel(): void {
    this.dialogRef.close(null);
  }
}
