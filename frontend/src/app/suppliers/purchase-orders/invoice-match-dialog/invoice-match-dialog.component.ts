import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule } from '@ngneat/transloco';
import { InvoiceMatchResult, InvoiceMatchItem } from '../../suppliers.service';

export interface InvoiceMatchDialogData {
  matchResult: InvoiceMatchResult;
  poId: number;
}

@Component({
  selector: 'app-invoice-match-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    TranslocoModule
  ],
  template: `
    <ng-container *transloco="let t">
      <h2 mat-dialog-title>
        <mat-icon>compare_arrows</mat-icon>
        {{ t('purchaseOrders.invoiceMatching.title') }}
      </h2>
      
      <mat-dialog-content>
        <!-- Invoice Summary -->
        <div class="invoice-summary">
          <div class="summary-item">
            <span class="label">{{ t('purchaseOrders.invoiceMatching.invoiceNumber') }}</span>
            <span class="value">{{ data.matchResult.invoice_number || 'N/A' }}</span>
          </div>
          <div class="summary-item">
            <span class="label">{{ t('purchaseOrders.invoiceMatching.vendor') }}</span>
            <span class="value">{{ data.matchResult.vendor_name || 'N/A' }}</span>
          </div>
          <div class="summary-item">
            <span class="label">{{ t('purchaseOrders.invoiceMatching.confidence') }}</span>
            <span class="value" [class.high]="data.matchResult.overall_confidence > 0.8"
                  [class.medium]="data.matchResult.overall_confidence >= 0.5 && data.matchResult.overall_confidence <= 0.8"
                  [class.low]="data.matchResult.overall_confidence < 0.5">
              {{ (data.matchResult.overall_confidence * 100) | number:'1.0-0' }}%
            </span>
          </div>
        </div>

        <!-- Matches Table -->
        <h3>{{ t('purchaseOrders.invoiceMatching.matchedItems') }}</h3>
        <table mat-table [dataSource]="data.matchResult.matches" class="match-table" *ngIf="data.matchResult.matches.length > 0">
          <!-- Status Column -->
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>{{ t('common.status') }}</th>
            <td mat-cell *matCellDef="let item">
              <mat-chip [class]="'status-' + item.match_status">
                {{ getStatusLabel(item.match_status) }}
              </mat-chip>
            </td>
          </ng-container>

          <!-- PO Description Column -->
          <ng-container matColumnDef="po_desc">
            <th mat-header-cell *matHeaderCellDef>{{ t('purchaseOrders.invoiceMatching.poItem') }}</th>
            <td mat-cell *matCellDef="let item">
              <div class="item-desc">
                <span>{{ item.po_description || 'N/A' }}</span>
                <small>Qty: {{ item.po_quantity | number:'1.0-0' }} @ {{ item.po_unit_cost | currency }}</small>
              </div>
            </td>
          </ng-container>

          <!-- Invoice Description Column -->
          <ng-container matColumnDef="invoice_desc">
            <th mat-header-cell *matHeaderCellDef>{{ t('purchaseOrders.invoiceMatching.invoiceItem') }}</th>
            <td mat-cell *matCellDef="let item">
              <div class="item-desc">
                <span>{{ item.invoice_description }}</span>
                <small>
                  <span *ngIf="item.invoice_sku">[{{ item.invoice_sku }}]</span>
                  Qty: {{ item.invoice_quantity | number:'1.0-0' }} @ {{ item.invoice_unit_cost | currency }}
                </small>
              </div>
            </td>
          </ng-container>

          <!-- Discrepancy Column -->
          <ng-container matColumnDef="discrepancy">
            <th mat-header-cell *matHeaderCellDef>{{ t('purchaseOrders.invoiceMatching.discrepancy') }}</th>
            <td mat-cell *matCellDef="let item">
              <span class="discrepancy-text" *ngIf="item.discrepancy_details">
                {{ item.discrepancy_details }}
              </span>
              <mat-icon *ngIf="!item.discrepancy_details" class="ok-icon">check_circle</mat-icon>
            </td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedColumns;" [class.has-discrepancy]="row.discrepancy_details"></tr>
        </table>

        <p class="no-items" *ngIf="data.matchResult.matches.length === 0">
          {{ t('purchaseOrders.invoiceMatching.noMatches') }}
        </p>

        <!-- Unmatched Items -->
        <div class="unmatched-section" *ngIf="data.matchResult.unmatched_po_items.length > 0">
          <h4>{{ t('purchaseOrders.invoiceMatching.unmatchedPO') }}</h4>
          <ul>
            <li *ngFor="let item of data.matchResult.unmatched_po_items">
              {{ item.product_name }} (Qty: {{ item.quantity }})
            </li>
          </ul>
        </div>

        <div class="unmatched-section" *ngIf="data.matchResult.unmatched_invoice_items.length > 0">
          <h4>{{ t('purchaseOrders.invoiceMatching.unmatchedInvoice') }}</h4>
          <ul>
            <li *ngFor="let item of data.matchResult.unmatched_invoice_items">
              {{ item.description }} (Qty: {{ item.quantity }})
            </li>
          </ul>
        </div>

        <!-- Total Discrepancy -->
        <div class="total-discrepancy" *ngIf="data.matchResult.total_discrepancy > 0">
          <mat-icon>warning</mat-icon>
          <span>{{ t('purchaseOrders.invoiceMatching.totalDiscrepancy') }}: 
            <strong>{{ data.matchResult.total_discrepancy | currency }}</strong>
          </span>
        </div>
      </mat-dialog-content>

      <mat-dialog-actions align="end">
        <button mat-button mat-dialog-close>{{ t('common.close') }}</button>
        <button mat-raised-button color="primary" (click)="applyInvoiceValues()"
            [disabled]="data.matchResult.matches.length === 0"
            [matTooltip]="t('purchaseOrders.invoiceMatching.applyTooltip')">
          <mat-icon>check_circle</mat-icon>
          {{ t('purchaseOrders.invoiceMatching.applyValues') }}
        </button>
        <button mat-raised-button color="accent" (click)="receiveMatchedItems()"
            [disabled]="getReceivableMatchCount() === 0"
            [matTooltip]="t('purchaseOrders.invoiceMatching.receiveTooltip')">
          <mat-icon>inventory_2</mat-icon>
          {{ t('purchaseOrders.invoiceMatching.receiveMatched') }}
        </button>
      </mat-dialog-actions>
    </ng-container>
  `,
  styles: [`
    h2[mat-dialog-title] {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    
    .invoice-summary {
      display: flex;
      gap: 24px;
      padding: 16px;
      background: #f5f5f5;
      border-radius: 8px;
      margin-bottom: 16px;
    }
    
    .summary-item {
      display: flex;
      flex-direction: column;
    }
    
    .summary-item .label {
      font-size: 12px;
      color: #666;
    }
    
    .summary-item .value {
      font-size: 18px;
      font-weight: 500;
    }
    
    .summary-item .value.high { color: #4caf50; }
    .summary-item .value.medium { color: #ff9800; }
    .summary-item .value.low { color: #f44336; }
    
    .match-table {
      width: 100%;
      margin-bottom: 16px;
    }
    
    .item-desc {
      display: flex;
      flex-direction: column;
    }
    
    .item-desc small {
      color: #666;
      font-size: 11px;
    }
    
    .status-matched { background-color: #c8e6c9 !important; }
    .status-quantity_diff { background-color: #fff3e0 !important; }
    .status-price_diff { background-color: #ffecb3 !important; }
    .status-quantity_price_diff { background-color: #ffcdd2 !important; }
    .status-unmatched { background-color: #e0e0e0 !important; }
    
    .has-discrepancy {
      background-color: #fff8e1;
    }
    
    .discrepancy-text {
      color: #e65100;
      font-size: 12px;
    }
    
    .ok-icon {
      color: #4caf50;
    }
    
    .unmatched-section {
      margin-top: 16px;
      padding: 12px;
      background: #fafafa;
      border-radius: 4px;
    }
    
    .unmatched-section h4 {
      margin: 0 0 8px 0;
      color: #666;
    }
    
    .unmatched-section ul {
      margin: 0;
      padding-left: 20px;
    }
    
    .total-discrepancy {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 16px;
      padding: 12px;
      background: #fff3e0;
      border-radius: 4px;
      color: #e65100;
    }
    
    .no-items {
      color: #666;
      text-align: center;
      padding: 24px;
    }
  `]
})
export class InvoiceMatchDialogComponent {
  displayedColumns = ['status', 'po_desc', 'invoice_desc', 'discrepancy'];

  constructor(
    public dialogRef: MatDialogRef<InvoiceMatchDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: InvoiceMatchDialogData
  ) { }

  getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      'matched': '✓ Match',
      'quantity_diff': 'Qty Diff',
      'price_diff': 'Price Diff',
      'quantity_price_diff': 'Qty+Price',
      'unmatched': 'No Match'
    };
    return labels[status] || status;
  }

  applyInvoiceValues(): void {
    // Return the match result with action flag for the parent component to apply
    this.dialogRef.close({
      action: 'apply',
      matchResult: this.data.matchResult
    });
  }

  receiveMatchedItems(): void {
    this.dialogRef.close({
      action: 'receive',
      matchResult: this.data.matchResult
    });
  }

  getReceivableMatchCount(): number {
    return (this.data.matchResult.matches || []).filter(
      (match) => !!match.po_item_id && match.match_status !== 'unmatched' && match.invoice_quantity > 0
    ).length;
  }
}
