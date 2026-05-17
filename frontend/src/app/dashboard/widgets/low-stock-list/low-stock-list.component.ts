import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Router, RouterModule } from '@angular/router';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';

import { LowStockReport, LowStockRow, LowStockService } from '../../services/low-stock.service';

@Component({
  selector: 'app-low-stock-list',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatCheckboxModule,
    MatSnackBarModule,
    RouterModule,
    TranslocoModule,
  ],
  templateUrl: './low-stock-list.component.html',
  styleUrls: ['./low-stock-list.component.scss'],
})
export class LowStockListWidgetComponent {
  @Input() report: LowStockReport | null = null;
  /** Emitted after a successful bulk reorder so the parent can refresh
   *  the report (the reordered items are still low until the PO is
   *  received — but the dashboard should refresh anyway in case
   *  another widget needs to react). */
  @Output() reordered = new EventEmitter<void>();

  /** product_ids the user has ticked for bulk reorder. */
  selectedIds = new Set<number>();
  isReordering = false;

  constructor(
    private lowStockService: LowStockService,
    private snackBar: MatSnackBar,
    private transloco: TranslocoService,
    private router: Router,
  ) {}

  get rows(): LowStockRow[] {
    return this.report?.rows ?? [];
  }

  get summary(): { critical: number; low: number; watch: number } {
    return {
      critical: this.report?.total_critical ?? 0,
      low: this.report?.total_low ?? 0,
      watch: this.report?.total_watch ?? 0,
    };
  }

  daysLeftLabel(row: LowStockRow): string {
    if (!row.daily_velocity || row.daily_velocity <= 0) return '—';
    if (row.days_of_inventory >= 999) return '—';
    return `${row.days_of_inventory.toFixed(1)}d`;
  }

  velocityLabel(row: LowStockRow): string {
    if (!row.daily_velocity || row.daily_velocity <= 0) return '—';
    return `${row.daily_velocity.toFixed(2)}/day`;
  }

  // ------------------------------------------------------------------
  // Bulk-reorder selection helpers
  // ------------------------------------------------------------------

  isSelected(productId: number): boolean {
    return this.selectedIds.has(productId);
  }

  toggleRow(productId: number, checked: boolean): void {
    if (checked) this.selectedIds.add(productId);
    else this.selectedIds.delete(productId);
  }

  get allSelected(): boolean {
    return this.rows.length > 0 && this.rows.every(r => this.selectedIds.has(r.product_id));
  }

  get someSelected(): boolean {
    return this.selectedIds.size > 0 && !this.allSelected;
  }

  toggleAll(checked: boolean): void {
    if (checked) {
      for (const r of this.rows) this.selectedIds.add(r.product_id);
    } else {
      this.selectedIds.clear();
    }
  }

  reorderSelected(): void {
    if (this.selectedIds.size === 0 || this.isReordering) return;
    this.isReordering = true;
    const ids = Array.from(this.selectedIds);

    this.lowStockService.reorderProducts(ids).subscribe({
      next: (resp) => {
        this.isReordering = false;
        const created = resp.created_purchase_orders ?? [];
        const skipped = resp.skipped ?? [];

        if (created.length === 0) {
          // All selected products were skipped — show what blocked them.
          this.snackBar.open(
            this.transloco.translate('dashboard.lowStock.reorderAllSkipped', { count: skipped.length }),
            this.transloco.translate('common.close'),
            { duration: 6000, panelClass: ['snackbar-error'] },
          );
          return;
        }

        // Successful creates — clear selection, emit refresh signal.
        this.selectedIds.clear();
        this.reordered.emit();

        if (created.length === 1) {
          const po = created[0];
          // Single PO: snackbar + a "View" action that navigates to it.
          const ref = this.snackBar.open(
            this.transloco.translate('dashboard.lowStock.reorderCreatedOne', {
              supplier: po.supplier_name,
              count: po.product_count,
            }),
            this.transloco.translate('dashboard.lowStock.viewPo'),
            { duration: 8000, panelClass: ['snackbar-success'] },
          );
          ref.onAction().subscribe(() => {
            this.router.navigate(['/suppliers/po', po.purchase_order_id, 'edit']);
          });
        } else {
          // Multiple POs: summarize counts; the user can find them on the PO list.
          this.snackBar.open(
            this.transloco.translate('dashboard.lowStock.reorderCreatedMany', {
              count: created.length,
              products: created.reduce((acc, po) => acc + po.product_count, 0),
            }),
            this.transloco.translate('common.close'),
            { duration: 8000, panelClass: ['snackbar-success'] },
          );
        }

        if (skipped.length > 0) {
          // Surface skipped count + the first product so the user knows
          // there's follow-up work (typically linking a supplier).
          const first = skipped[0];
          this.snackBar.open(
            this.transloco.translate('dashboard.lowStock.reorderPartialSkipped', {
              count: skipped.length,
              first: first.product_name ?? `#${first.product_id}`,
            }),
            this.transloco.translate('common.close'),
            { duration: 10000, panelClass: ['snackbar-error'] },
          );
        }
      },
      error: () => {
        this.isReordering = false;
        // HttpErrorInterceptor surfaces the localized backend message.
      },
    });
  }
}
