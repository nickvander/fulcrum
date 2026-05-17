import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { TranslocoModule } from '@ngneat/transloco';

import {
  AllocationEntry,
  InventorySnapshotRow,
  STOCK_LOCATION_AMAZON_FBA,
  STOCK_LOCATION_INTERNAL,
  STOCK_LOCATION_ML_FULL,
  StockTransferService,
} from '../stock-transfer.service';

interface PlannerRow {
  productId: number;
  productName: string;
  sku?: string | null;
  internal: number;
  mlFull: number;
  amazonFba: number;
  allocateMl: number;
  allocateAmazon: number;
}

@Component({
  selector: 'app-stock-transfer-planner',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTableModule,
    TranslocoModule,
  ],
  templateUrl: './stock-transfer-planner.html',
  styleUrl: './stock-transfer-planner.scss',
})
export class StockTransferPlannerComponent implements OnInit {
  rows: PlannerRow[] = [];
  loading = false;
  saving = false;
  notes = '';
  search = '';
  readonly columns = [
    'product',
    'internal',
    'mlFull',
    'amazonFba',
    'allocateMl',
    'allocateAmazon',
    'remaining',
  ];

  constructor(
    private service: StockTransferService,
    private snackBar: MatSnackBar,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.loading = true;
    this.service.inventorySnapshot().subscribe({
      next: snapshot => {
        this.rows = snapshot.map(row => this.toPlannerRow(row));
        this.loading = false;
      },
      error: err => {
        console.error('Snapshot load failed', err);
        this.loading = false;
        this.snackBar.open('Failed to load inventory snapshot', 'Close', {
          duration: 4000,
        });
      },
    });
  }

  private toPlannerRow(row: InventorySnapshotRow): PlannerRow {
    return {
      productId: row.product_id,
      productName: row.product_name,
      sku: row.product_sku,
      internal: row.by_location[STOCK_LOCATION_INTERNAL] ?? 0,
      mlFull: row.by_location[STOCK_LOCATION_ML_FULL] ?? 0,
      amazonFba: row.by_location[STOCK_LOCATION_AMAZON_FBA] ?? 0,
      allocateMl: 0,
      allocateAmazon: 0,
    };
  }

  get filteredRows(): PlannerRow[] {
    const term = this.search.trim().toLowerCase();
    if (!term) {
      return this.rows;
    }
    return this.rows.filter(
      r =>
        r.productName.toLowerCase().includes(term) ||
        (r.sku || '').toLowerCase().includes(term),
    );
  }

  remaining(row: PlannerRow): number {
    return row.internal - (row.allocateMl + row.allocateAmazon);
  }

  isOver(row: PlannerRow): boolean {
    return this.remaining(row) < 0;
  }

  updateAlloc(row: PlannerRow, field: 'allocateMl' | 'allocateAmazon', value: unknown): void {
    const next = Number(value);
    row[field] = Number.isFinite(next) && next > 0 ? Math.floor(next) : 0;
  }

  totalToAllocate(): number {
    return this.rows.reduce(
      (sum, r) => sum + r.allocateMl + r.allocateAmazon,
      0,
    );
  }

  canSave(): boolean {
    if (this.saving || this.totalToAllocate() === 0) {
      return false;
    }
    return !this.rows.some(r => this.isOver(r));
  }

  save(): void {
    if (!this.canSave()) {
      return;
    }
    const allocations: AllocationEntry[] = [];
    for (const row of this.rows) {
      if (row.allocateMl > 0) {
        allocations.push({
          product_id: row.productId,
          dest_location: STOCK_LOCATION_ML_FULL,
          qty_planned: row.allocateMl,
        });
      }
      if (row.allocateAmazon > 0) {
        allocations.push({
          product_id: row.productId,
          dest_location: STOCK_LOCATION_AMAZON_FBA,
          qty_planned: row.allocateAmazon,
        });
      }
    }
    this.saving = true;
    this.service.planAllocations(allocations, this.notes).subscribe({
      next: drafts => {
        this.saving = false;
        this.snackBar.open(`${drafts.length} draft transfer(s) created`, 'Close', {
          duration: 3000,
        });
        this.router.navigate(['/marketplaces/transfers']);
      },
      error: err => {
        this.saving = false;
        // HttpErrorInterceptor surfaces the localized backend message.
      },
    });
  }
}
