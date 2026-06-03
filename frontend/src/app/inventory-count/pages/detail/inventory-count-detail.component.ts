import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { Subject, takeUntil } from 'rxjs';

import { ConfirmationDialog, ConfirmationDialogData } from '../../../shared/components/confirmation-dialog/confirmation-dialog';
import { ScanSkuDialogComponent } from '../../components/scan-sku-dialog/scan-sku-dialog.component';
import {
  InventoryCountItem,
  InventoryCountService,
  InventoryCountSessionDetail,
} from '../../services/inventory-count.service';


/**
 * Session detail page.
 *
 * Header surfaces the session's lifecycle state + a Commit / Cancel
 * pair when in-progress. Body has an "Add SKU" input (single-shot
 * type-and-enter or scan-and-enter) followed by a Material table of
 * the items already in the session. Each row shows
 * {SKU, name, expected, counted (editable), delta}.
 *
 * Counted_quantity edits debounce 400 ms — the operator typing "42"
 * shouldn't fire four PATCHes for "4", "42", … etc. Items the
 * operator hasn't touched yet stay at counted=null (skipped on
 * commit).
 *
 * Commit: confirmation dialog summarizing how many adjustments will
 * fire + items skipped. Cancel: confirmation explaining no
 * adjustments will be written. Both routes back to the list page
 * with a snackbar.
 */
@Component({
  selector: 'app-inventory-count-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTableModule,
    MatTooltipModule,
    TranslocoModule,
  ],
  templateUrl: './inventory-count-detail.component.html',
  styleUrl: './inventory-count-detail.component.scss',
})
export class InventoryCountDetailComponent implements OnInit, OnDestroy {
  /** i18n key for a session status (avoids rendering the raw enum). */
  statusLabelKey(status: string): string {
    if (status === 'in_progress') return 'inventoryCount.list.statusInProgress';
    if (status === 'committed') return 'inventoryCount.list.statusCommitted';
    if (status === 'cancelled') return 'inventoryCount.list.statusCancelled';
    return 'inventoryCount.list.statusAll';
  }

  session: InventoryCountSessionDetail | null = null;
  loading = false;
  errored = false;
  addingSku = '';
  addingInFlight = false;
  committing = false;
  cancelling = false;

  /** Track per-item pending count updates so the input doesn't
   *  rebound from the server before the operator finishes typing.
   *  Keyed by item id. */
  pendingCounts = new Map<number, number | null>();

  readonly displayedColumns = ['sku', 'name', 'expected', 'counted', 'delta', 'actions'];

  private destroy$ = new Subject<void>();

  constructor(
    private route: ActivatedRoute,
    private countService: InventoryCountService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private transloco: TranslocoService,
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (Number.isFinite(id)) {
      this.load(id);
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  load(sessionId: number): void {
    this.loading = true;
    this.errored = false;
    this.countService.get(sessionId).pipe(takeUntil(this.destroy$)).subscribe({
      next: (s) => {
        this.session = s;
        this.loading = false;
      },
      error: () => {
        this.errored = true;
        this.loading = false;
      },
    });
  }

  get isInProgress(): boolean {
    return this.session?.status === 'in_progress';
  }

  /** Open the lightweight scan dialog. On a successful scan or
   *  manual submit it returns the SKU string; we plug it into the
   *  add-SKU input and submit immediately. The operator's flow is:
   *  tap "Scan" → point camera at label → row appears on the page.
   */
  openScanner(): void {
    if (!this.session || !this.isInProgress || this.addingInFlight) return;
    const ref = this.dialog.open(ScanSkuDialogComponent, {
      width: '92vw',
      maxWidth: '500px',
      // The scan dialog manages its own video lifecycle in
      // ngOnDestroy, so closing via backdrop or escape is safe.
    });
    ref.afterClosed().subscribe((value?: string) => {
      const v = (value || '').trim();
      if (!v) return;
      this.addingSku = v;
      this.addItem();
    });
  }

  addItem(): void {
    const sku = this.addingSku.trim();
    if (!sku || !this.session || this.addingInFlight) return;
    this.addingInFlight = true;
    this.countService.addItem(this.session.id, sku).subscribe({
      next: (item) => {
        this.addingInFlight = false;
        // Append to the items list locally so the operator sees
        // the row appear immediately.
        if (this.session) {
          this.session.items = [...this.session.items, item];
          this.session.item_count += 1;
        }
        this.addingSku = '';
      },
      error: (err) => {
        this.addingInFlight = false;
        const code = err?.error?.code;
        let key = 'inventoryCount.detail.addFailed';
        if (code === 'apiErrors.product.notFoundBySku') {
          key = 'inventoryCount.detail.skuNotFound';
        } else if (code === 'apiErrors.inventoryCount.skuAlreadyInSession') {
          key = 'inventoryCount.detail.skuAlreadyAdded';
        }
        this.snackBar.open(
          this.transloco.translate(key, { sku }),
          this.transloco.translate('common.close'),
          { duration: 4000 },
        );
      },
    });
  }

  /** PATCH the count for one row immediately. Called from the
   *  input's (change) handler so we only fire on blur / Enter
   *  rather than every keystroke. */
  saveCount(item: InventoryCountItem, value: string): void {
    if (!this.session) return;
    const parsed = value === '' ? null : Number(value);
    const counted = parsed === null || Number.isNaN(parsed) ? null : Math.floor(parsed);
    this.countService.updateCount(this.session.id, item.id, counted).subscribe({
      next: (updated) => {
        item.counted_quantity = updated.counted_quantity;
      },
      error: () => {
        this.snackBar.open(
          this.transloco.translate('inventoryCount.detail.updateFailed'),
          this.transloco.translate('common.close'),
          { duration: 4000 },
        );
      },
    });
  }

  removeItem(item: InventoryCountItem): void {
    if (!this.session) return;
    this.countService.removeItem(this.session.id, item.id).subscribe({
      next: () => {
        if (this.session) {
          this.session.items = this.session.items.filter(i => i.id !== item.id);
          this.session.item_count = Math.max(0, this.session.item_count - 1);
        }
      },
      error: () => {
        this.snackBar.open(
          this.transloco.translate('inventoryCount.detail.removeFailed'),
          this.transloco.translate('common.close'),
          { duration: 4000 },
        );
      },
    });
  }

  delta(item: InventoryCountItem): number | null {
    if (item.counted_quantity === null || item.counted_quantity === undefined) return null;
    return item.counted_quantity - item.expected_quantity;
  }

  deltaClass(item: InventoryCountItem): string {
    const d = this.delta(item);
    if (d === null) return '';
    if (d === 0) return 'delta-zero';
    return d > 0 ? 'delta-positive' : 'delta-negative';
  }

  /**
   * A counted line is "out of tolerance" (worth a recount) when its variance is
   * large in absolute units OR as a share of expected. Surfaced as a "Revisar"
   * flag so a mis-count doesn't quietly post a big adjustment.
   */
  private static readonly VARIANCE_ABS = 10;
  private static readonly VARIANCE_PCT = 0.05;

  isOutOfTolerance(item: InventoryCountItem): boolean {
    const d = this.delta(item);
    if (d === null || d === 0) return false;
    const abs = Math.abs(d);
    const pct = item.expected_quantity > 0 ? abs / item.expected_quantity : 1;
    return abs > InventoryCountDetailComponent.VARIANCE_ABS || pct > InventoryCountDetailComponent.VARIANCE_PCT;
  }

  outOfToleranceCount(): number {
    if (!this.session) return 0;
    return this.session.items.filter(i => this.isOutOfTolerance(i)).length;
  }

  /** Operator preview: how many adjustments will the commit fire?
   *  Mirrors the service's gate. */
  pendingAdjustmentCount(): number {
    if (!this.session) return 0;
    return this.session.items.filter(item => {
      if (item.counted_quantity === null || item.counted_quantity === undefined) return false;
      return item.counted_quantity !== item.expected_quantity;
    }).length;
  }

  commit(): void {
    if (!this.session || this.committing) return;
    const willFire = this.pendingAdjustmentCount();
    const review = this.outOfToleranceCount();

    let message = this.transloco.translate('inventoryCount.detail.commitConfirmBody', { n: willFire });
    if (review > 0) {
      message += ' ' + this.transloco.translate('inventoryCount.detail.commitReviewWarning', { n: review });
    }

    const ref = this.dialog.open(ConfirmationDialog, {
      data: {
        title: this.transloco.translate('inventoryCount.detail.commitConfirmTitle'),
        message,
      } as ConfirmationDialogData,
    });

    ref.afterClosed().subscribe((ok) => {
      if (!ok || !this.session) return;
      this.committing = true;
      this.countService.commit(this.session.id).subscribe({
        next: (result) => {
          this.committing = false;
          this.session = result.session;
          this.snackBar.open(
            this.transloco.translate('inventoryCount.detail.commitSnackbar', {
              n: result.adjustments_created,
            }),
            this.transloco.translate('common.close'),
            { duration: 4000 },
          );
        },
        error: () => {
          this.committing = false;
          this.snackBar.open(
            this.transloco.translate('inventoryCount.detail.commitFailed'),
            this.transloco.translate('common.close'),
            { duration: 4000 },
          );
        },
      });
    });
  }

  cancelSession(): void {
    if (!this.session || this.cancelling) return;
    const ref = this.dialog.open(ConfirmationDialog, {
      data: {
        title: this.transloco.translate('inventoryCount.detail.cancelConfirmTitle'),
        message: this.transloco.translate('inventoryCount.detail.cancelConfirmBody'),
      } as ConfirmationDialogData,
    });

    ref.afterClosed().subscribe((ok) => {
      if (!ok || !this.session) return;
      this.cancelling = true;
      this.countService.cancel(this.session.id).subscribe({
        next: (s) => {
          this.cancelling = false;
          this.session = s;
        },
        error: () => {
          this.cancelling = false;
          this.snackBar.open(
            this.transloco.translate('inventoryCount.detail.cancelFailed'),
            this.transloco.translate('common.close'),
            { duration: 4000 },
          );
        },
      });
    });
  }
}
