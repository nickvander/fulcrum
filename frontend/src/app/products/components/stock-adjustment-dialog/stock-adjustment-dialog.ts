import { ChangeDetectionStrategy, Component, Inject, computed, signal } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';

import { FormsModule } from '@angular/forms';
import { MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { QuantityStepperComponent } from '../../../shared/components/quantity-stepper/quantity-stepper.component';

export interface StockAdjustmentData {
  productName: string;
  currentQuantity: number;
  /** i18n key for the inventory location being adjusted. Defaults to the warehouse (Bodega). */
  locationLabelKey?: string;
  /** True when the adjusted location is the local warehouse, so we can warn that ML Full is unaffected. */
  isWarehouse?: boolean;
}

export interface StockAdjustmentResult {
  adjustment: number;
  reason?: string;
}

/** Reason codes for a manual stock adjustment (founder-approved taxonomy). */
const REASON_CODES = [
  { value: 'received', labelKey: 'products.adjustReason.received' },
  { value: 'count', labelKey: 'products.adjustReason.count' },
  { value: 'damaged', labelKey: 'products.adjustReason.damaged' },
  { value: 'theft', labelKey: 'products.adjustReason.theft' },
  { value: 'return', labelKey: 'products.adjustReason.return' },
  { value: 'dataEntry', labelKey: 'products.adjustReason.dataEntry' },
] as const;

@Component({
  selector: 'app-stock-adjustment-dialog',
  templateUrl: './stock-adjustment-dialog.html',
  styleUrls: ['./stock-adjustment-dialog.scss'],
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    TranslocoModule,
    QuantityStepperComponent,
  ],
})
export class StockAdjustmentDialog {
  readonly reasonCodes = REASON_CODES;
  readonly locationLabelKey: string;

  adjustment = signal(0);
  reasonCode = signal<string>('');
  note = '';
  showConfirmation = signal(false);

  readonly resultingStock = computed(() => this.data.currentQuantity + Number(this.adjustment() || 0));
  readonly wouldGoNegative = computed(() => this.resultingStock() < 0);
  /** Large-delta guard: |delta| exceeds current stock or 50 units. */
  readonly isLargeDelta = computed(() => {
    const d = Math.abs(Number(this.adjustment() || 0));
    return d > 0 && (d > Math.max(this.data.currentQuantity, 1) || d > 50);
  });

  constructor(
    public dialogRef: MatDialogRef<StockAdjustmentDialog>,
    private transloco: TranslocoService,
    @Inject(MAT_DIALOG_DATA) public data: StockAdjustmentData,
  ) {
    this.locationLabelKey = data.locationLabelKey ?? 'products.bucketDefault';
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onAdjustmentChange(): void {
    this.showConfirmation.set(false);
  }

  canPreview(): boolean {
    const d = Number(this.adjustment() || 0);
    return d !== 0 && !!this.reasonCode() && !this.wouldGoNegative();
  }

  confirmAdjustment(): void {
    if (this.canPreview()) this.showConfirmation.set(true);
  }

  /** Compose a human-readable reason (code label + optional note) for the audit trail. */
  private composeReason(): string {
    const codeLabel = this.transloco.translate(
      REASON_CODES.find((r) => r.value === this.reasonCode())?.labelKey ?? 'products.reason',
    );
    const note = this.note?.trim();
    return note ? `${codeLabel} — ${note}` : codeLabel;
  }

  confirmAndClose(): void {
    this.dialogRef.close({ adjustment: Number(this.adjustment()), reason: this.composeReason() } as StockAdjustmentResult);
  }

  goBack(): void {
    this.showConfirmation.set(false);
  }
}
