import { Component, Inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { CommonModule } from '@angular/common';
import { MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { OrderByPipe } from '../../pipes/order-by.pipe';
import { DatePipe } from '@angular/common';

export interface StockHistoryDialogData {
  productName: string;
  currentStock: number;
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
    MatIconModule,
    OrderByPipe,
    DatePipe
  ],
  template: `
    <h2 mat-dialog-title>Stock Adjustment History for {{ data.productName }}</h2>
    <mat-dialog-content>
      <div class="current-stock-info">
        <mat-icon>inventory_2</mat-icon>
        <div class="current-stock-text">
          <span class="current-stock-label">Current Stock:</span>
          <span class="current-stock-value">{{ data.currentStock }}</span>
        </div>
      </div>
      
      <div *ngIf="data.inventoryAdjustments.length === 0; else historyList" class="no-history">
        <p>No stock adjustments recorded yet.</p>
      </div>
      
      <ng-template #historyList>
        <mat-list>
          <mat-list-item *ngFor="let adjustment of data.inventoryAdjustments | orderBy:'timestamp':true" class="adjustment-item">
            <div class="adjustment-content">
              <div class="adjustment-main">
                <div class="adjustment-amount-container">
                  <div class="adjustment-amount" [class.positive]="adjustment.adjustment > 0" [class.negative]="adjustment.adjustment < 0">
                    <span class="adjustment-sign">{{ adjustment.adjustment > 0 ? '+' : '' }}</span>
                    <span class="adjustment-value">{{ adjustment.adjustment }}</span>
                  </div>
                </div>
                
                <div class="adjustment-details">
                  <div class="adjustment-date-user">
                    <span class="adjustment-date">{{ adjustment.timestamp | date:'short' }}</span>
                    <span class="adjustment-user" *ngIf="adjustment.created_by">• {{ adjustment.created_by }}</span>
                  </div>
                  <div class="adjustment-reason" *ngIf="adjustment.reason">
                    <mat-icon class="reason-icon">info</mat-icon>
                    <span>{{ adjustment.reason }}</span>
                  </div>
                </div>
              </div>
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
    
    .current-stock-info {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px;
      border-radius: 8px;
      background-color: #f5f9ff;
      border: 1px solid #d1e7ff;
      margin-bottom: 20px;
      font-weight: 500;
    }
    
    .current-stock-text {
      display: flex;
      flex-direction: column;
    }
    
    .current-stock-label {
      font-size: 0.9em;
      color: #666;
    }
    
    .current-stock-value {
      font-size: 1.8em;
      font-weight: bold;
      color: #1976d2;
      margin-top: 4px;
    }
    
    .adjustment-item {
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      margin-bottom: 12px;
      padding: 16px;
      background-color: #fafafa;
    }
    
    .adjustment-content {
      width: 100%;
    }
    
    .adjustment-main {
      display: flex;
      gap: 16px;
    }
    
    .adjustment-amount-container {
      min-width: 80px;
      display: flex;
      align-items: flex-start;
      justify-content: center;
    }
    
    .adjustment-amount {
      display: inline-flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-width: 60px;
      padding: 8px 12px;
      border-radius: 8px;
      font-weight: bold;
      font-size: 1em;
      text-align: center;
      border: 1px solid;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .positive {
      background-color: #e8f5e9;
      color: #4caf50;
      border-color: #c8e6c9;
    }
    
    .negative {
      background-color: #ffebee;
      color: #f44336;
      border-color: #ffcdd2;
    }
    
    .adjustment-amount .adjustment-sign {
      font-size: 0.9em;
      line-height: 1;
    }
    
    .adjustment-amount .adjustment-value {
      font-size: 1.2em;
      line-height: 1;
      font-weight: 700;
    }
    
    .adjustment-details {
      flex: 1;
    }
    
    .adjustment-date-user {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;
    }
    
    .adjustment-date {
      font-size: 0.9em;
      color: #666;
      font-weight: 500;
    }
    
    .adjustment-user {
      font-size: 0.9em;
      color: #888;
    }
    
    .adjustment-reason {
      display: flex;
      align-items: flex-start;
      gap: 6px;
      font-size: 0.85em;
      color: #666;
      font-style: italic;
      margin-top: 6px;
      padding-left: 4px;
    }
    
    .reason-icon {
      font-size: 1em;
      width: 1em;
      height: 1em;
      color: #666;
      margin-top: 2px;
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