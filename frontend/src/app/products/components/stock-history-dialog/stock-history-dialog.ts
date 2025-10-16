import { Component, Inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { CommonModule } from '@angular/common';
import { MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatListModule } from '@angular/material/list';
import { OrderByPipe } from '../../pipes/order-by.pipe';
import { DatePipe } from '@angular/common';

export interface StockHistoryDialogData {
  productName: string;
  inventoryAdjustments: Array<{
    id: number;
    adjustment: number;
    reason: string | null;
    timestamp: string;
    created_by: string | null;
  }>;
}

@Component({
  selector: 'app-stock-history-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatListModule,
    OrderByPipe,
    DatePipe
  ],
  template: `
    <h2 mat-dialog-title>Stock Adjustment History for {{ data.productName }}</h2>
    <mat-dialog-content>
      <div *ngIf="data.inventoryAdjustments.length === 0; else historyList" class="no-history">
        <p>No stock adjustments recorded yet.</p>
      </div>
      
      <ng-template #historyList>
        <mat-list>
          <mat-list-item *ngFor="let adjustment of data.inventoryAdjustments | orderBy:'timestamp':true" class="adjustment-item">
            <div class="adjustment-header" matListItemTitle>
              <span class="adjustment-amount" [class.positive]="adjustment.adjustment > 0" [class.negative]="adjustment.adjustment < 0">
                {{ adjustment.adjustment > 0 ? '+' : '' }}{{ adjustment.adjustment }}
              </span>
              <span class="adjustment-date">{{ adjustment.timestamp | date:'short' }}</span>
            </div>
            <div matListItemLine class="adjustment-reason" *ngIf="adjustment.reason">
              {{ adjustment.reason }}
            </div>
            <div matListItemLine class="adjustment-user" *ngIf="adjustment.created_by">
              By: {{ adjustment.created_by }}
            </div>
          </mat-list-item>
        </mat-list>
      </ng-template>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="onClose()" cdkFocusInitial>Close</button>
    </mat-dialog-actions>
  `,
  styles: [`
    .no-history {
      text-align: center;
      padding: 20px;
      color: #666;
    }
    
    .adjustment-item {
      border-bottom: 1px solid #eee;
      padding: 12px 0;
    }
    
    .adjustment-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .adjustment-amount {
      font-weight: bold;
      font-size: 1.1em;
    }
    
    .positive {
      color: #4caf50;
    }
    
    .negative {
      color: #f44336;
    }
    
    .adjustment-date {
      font-size: 0.85em;
      color: #666;
    }
    
    .adjustment-reason {
      font-style: italic;
      color: #666;
      margin-top: 4px;
    }
    
    .adjustment-user {
      font-size: 0.85em;
      color: #888;
    }
  `]
})
export class StockHistoryDialog {
  constructor(
    public dialogRef: MatDialogRef<StockHistoryDialog>,
    @Inject(MAT_DIALOG_DATA) public data: StockHistoryDialogData
  ) {}

  onClose(): void {
    this.dialogRef.close();
  }
}