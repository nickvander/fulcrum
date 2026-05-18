import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router } from '@angular/router';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { finalize } from 'rxjs';

import {
  AlertRule,
  AlertsService,
} from '../../services/alerts.service';
import {
  AlertFormDialogComponent,
  AlertFormDialogData,
  AlertFormDialogResult,
} from '../alert-form-dialog/alert-form-dialog.component';
import { ConfirmationDialog, ConfirmationDialogData } from '../../../shared/components/confirmation-dialog/confirmation-dialog';

@Component({
  selector: 'app-alerts-page',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatDialogModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSlideToggleModule,
    MatSnackBarModule,
    MatTableModule,
    MatTooltipModule,
    TranslocoModule,
  ],
  templateUrl: './alerts-page.component.html',
  styleUrls: ['./alerts-page.component.scss'],
})
export class AlertsPageComponent implements OnInit {
  rules: AlertRule[] = [];
  loading = false;
  /** Per-rule busy flag — keyed by rule.id — so the spinner only
   *  shows on the row whose Test button was clicked, not the whole
   *  table. */
  testing = new Set<number>();
  deleting = new Set<number>();
  togglingEnabled = new Set<number>();

  readonly displayedColumns = [
    'type', 'threshold', 'window', 'cooldown',
    'email', 'enabled', 'last_triggered', 'actions',
  ];

  constructor(
    private alertsService: AlertsService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private transloco: TranslocoService,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading = true;
    this.alertsService.list()
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: (rules) => (this.rules = rules),
        error: () => this.snack('alerts.errors.loadFailed'),
      });
  }

  openCreateDialog(): void {
    const dialogRef = this.dialog.open<
      AlertFormDialogComponent, AlertFormDialogData, AlertFormDialogResult | null
    >(AlertFormDialogComponent, {
      data: { mode: 'create' },
      width: '440px',
    });
    dialogRef.afterClosed().subscribe((result) => {
      if (!result || result.mode !== 'create') return;
      this.alertsService.create(result.payload as Parameters<AlertsService['create']>[0]).subscribe({
        next: () => {
          this.snack('alerts.messages.created');
          this.refresh();
        },
        error: () => this.snack('alerts.errors.createFailed'),
      });
    });
  }

  openEditDialog(rule: AlertRule): void {
    const dialogRef = this.dialog.open<
      AlertFormDialogComponent, AlertFormDialogData, AlertFormDialogResult | null
    >(AlertFormDialogComponent, {
      data: { mode: 'edit', rule },
      width: '440px',
    });
    dialogRef.afterClosed().subscribe((result) => {
      if (!result || result.mode !== 'edit') return;
      this.alertsService.update(rule.id, result.payload).subscribe({
        next: () => {
          this.snack('alerts.messages.updated');
          this.refresh();
        },
        error: () => this.snack('alerts.errors.updateFailed'),
      });
    });
  }

  toggleEnabled(rule: AlertRule, event: { checked: boolean }): void {
    if (this.togglingEnabled.has(rule.id)) return;
    this.togglingEnabled.add(rule.id);
    this.alertsService.update(rule.id, { enabled: event.checked })
      .pipe(finalize(() => this.togglingEnabled.delete(rule.id)))
      .subscribe({
        next: (updated) => {
          // Update the row in-place so the toggle stays consistent
          // even before the next refresh().
          const idx = this.rules.findIndex((r) => r.id === rule.id);
          if (idx >= 0) {
            this.rules = [
              ...this.rules.slice(0, idx),
              { ...this.rules[idx], enabled: updated.enabled },
              ...this.rules.slice(idx + 1),
            ];
          }
          this.snack(event.checked ? 'alerts.messages.enabled' : 'alerts.messages.disabled');
        },
        error: () => {
          // Revert the toggle visually by re-pulling the row.
          this.snack('alerts.errors.updateFailed');
          this.refresh();
        },
      });
  }

  test(rule: AlertRule): void {
    if (this.testing.has(rule.id)) return;
    this.testing.add(rule.id);
    this.alertsService.test(rule.id)
      .pipe(finalize(() => this.testing.delete(rule.id)))
      .subscribe({
        next: (result) => {
          if (result.triggered && result.notification_sent) {
            this.snack('alerts.messages.testTriggeredAndSent');
          } else if (result.triggered) {
            this.snack('alerts.messages.testTriggeredNotSent');
          } else {
            this.snack('alerts.messages.testNotTriggered');
          }
        },
        error: () => this.snack('alerts.errors.testFailed'),
      });
  }

  delete(rule: AlertRule): void {
    if (this.deleting.has(rule.id)) return;
    const ref = this.dialog.open<ConfirmationDialog, ConfirmationDialogData, boolean>(
      ConfirmationDialog,
      {
        width: '380px',
        data: {
          title: this.transloco.translate('alerts.delete.title'),
          message: this.transloco.translate('alerts.delete.message', {
            type: this.transloco.translate('alerts.type.' + rule.alert_type),
          }),
        },
      },
    );
    ref.afterClosed().subscribe((confirmed) => {
      if (!confirmed) return;
      this.deleting.add(rule.id);
      this.alertsService.delete(rule.id)
        .pipe(finalize(() => this.deleting.delete(rule.id)))
        .subscribe({
          next: () => {
            this.snack('alerts.messages.deleted');
            this.rules = this.rules.filter((r) => r.id !== rule.id);
          },
          error: () => this.snack('alerts.errors.deleteFailed'),
        });
    });
  }

  /** Compact threshold label for the table — units depend on type. */
  thresholdLabel(rule: AlertRule): string {
    if (rule.alert_type === 'low_margin' || rule.alert_type === 'sales_dip') {
      return `${rule.threshold}%`;
    }
    // stockout_risk: count
    return `${rule.threshold}`;
  }

  formatLastTriggered(iso: string | null | undefined): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleString();
  }

  private snack(key: string): void {
    this.snackBar.open(
      this.transloco.translate(key),
      this.transloco.translate('common.close'),
      { duration: 4000 },
    );
  }
}
