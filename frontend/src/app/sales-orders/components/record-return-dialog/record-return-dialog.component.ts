import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslocoModule } from '@ngneat/transloco';

import {
  RecordReturnLine,
  RecordReturnPayload,
  SalesOrderDetail,
  SalesOrderItem,
  SalesOrdersService,
} from '../../services/sales-orders.service';

export interface RecordReturnDialogData {
  order: SalesOrderDetail;
}

interface LineRow {
  item: SalesOrderItem;
  selected: boolean;
  /** Quantity the operator says came back. Defaults to the line's
   *  ordered quantity; the operator can edit down for partial
   *  returns. */
  quantity: number;
}

/**
 * Dialog where the operator records a physical return against a
 * sales order. Multi-select line items (a 3-SKU order might come
 * back as 2 SKUs), per-line quantity defaulting to the ordered
 * quantity, free-text reason + notes.
 *
 * The dialog stays light: validation runs on the client (selected
 * lines + positive quantities) and the backend is the source of
 * truth for "this item belongs to that order" checks.
 */
@Component({
  selector: 'app-record-return-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatCheckboxModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    TranslocoModule,
  ],
  templateUrl: './record-return-dialog.component.html',
  styleUrl: './record-return-dialog.component.scss',
})
export class RecordReturnDialogComponent {
  lines: LineRow[];
  reason = '';
  notes = '';
  saving = false;
  errorMessage: string | null = null;

  constructor(
    @Inject(MAT_DIALOG_DATA) public data: RecordReturnDialogData,
    private dialogRef: MatDialogRef<RecordReturnDialogComponent>,
    private salesOrders: SalesOrdersService,
  ) {
    // Build editable rows from the order's line items. Default
    // every checkbox to unchecked — operators are more often
    // returning one line than all lines, so opt-in is safer than
    // opt-out.
    this.lines = (data.order.items || []).map(item => ({
      item,
      selected: false,
      quantity: item.quantity || 1,
    }));
  }

  /** True iff at least one line is selected with quantity > 0. */
  canSubmit(): boolean {
    return this.selectedLines().length > 0 && !this.saving;
  }

  private selectedLines(): LineRow[] {
    return this.lines.filter(l => l.selected && l.quantity > 0);
  }

  submit(): void {
    const selected = this.selectedLines();
    if (selected.length === 0) {
      this.errorMessage = 'Select at least one line to return.';
      return;
    }
    this.saving = true;
    this.errorMessage = null;

    const payload: RecordReturnPayload = {
      lines: selected.map<RecordReturnLine>(l => ({
        order_item_id: l.item.id,
        quantity: l.quantity,
      })),
      reason: this.reason || null,
      notes: this.notes || null,
    };
    this.salesOrders.recordReturn(this.data.order.id, payload).subscribe({
      next: (rows) => {
        this.saving = false;
        // Pass the newly-created return rows back so the parent
        // page can append them to its history without a refetch.
        this.dialogRef.close({ created: rows });
      },
      error: (err) => {
        this.saving = false;
        this.errorMessage =
          err?.error?.detail || 'Could not record return. Please try again.';
      },
    });
  }

  cancel(): void {
    this.dialogRef.close(null);
  }
}
