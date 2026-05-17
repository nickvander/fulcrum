import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { TranslocoModule } from '@ngneat/transloco';

import { ProductService } from '../../../products/services/product';
import {
  STOCK_LOCATION_AMAZON_FBA,
  STOCK_LOCATION_INTERNAL,
  STOCK_LOCATION_ML_FULL,
  StockTransferCreateInput,
  StockTransferItemInput,
  StockTransferService,
} from '../stock-transfer.service';

interface SelectedRow {
  productId: number;
  productName: string;
  sku?: string | null;
  qtyPlanned: number;
}

@Component({
  selector: 'app-stock-transfer-create-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatSnackBarModule,
    MatTableModule,
    TranslocoModule,
  ],
  templateUrl: './stock-transfer-create-dialog.html',
  styleUrl: './stock-transfer-create-dialog.scss',
})
export class StockTransferCreateDialogComponent implements OnInit {
  destLocation = STOCK_LOCATION_ML_FULL;
  sourceLocation = STOCK_LOCATION_INTERNAL;
  notes = '';
  search = '';

  readonly destChoices = [
    { value: STOCK_LOCATION_ML_FULL, labelKey: 'stockTransfers.locations.mlFull' },
    { value: STOCK_LOCATION_AMAZON_FBA, labelKey: 'stockTransfers.locations.amazonFba' },
  ];

  products: { id: number; name: string; sku?: string | null }[] = [];
  selected: SelectedRow[] = [];
  saving = false;

  readonly selectedColumns = ['name', 'qty', 'actions'];

  constructor(
    public dialogRef: MatDialogRef<StockTransferCreateDialogComponent>,
    private productService: ProductService,
    private service: StockTransferService,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    this.productService.getProducts(1, 200).subscribe({
      next: response => {
        this.products = (response?.data || []).map(p => ({
          id: p.id,
          name: p.name,
          sku: p.sku,
        }));
      },
      error: err => console.error('Failed to load products', err),
    });
  }

  get filteredProducts(): { id: number; name: string; sku?: string | null }[] {
    const term = this.search.trim().toLowerCase();
    const selectedIds = new Set(this.selected.map(s => s.productId));
    const remaining = this.products.filter(p => !selectedIds.has(p.id));
    if (!term) {
      return remaining.slice(0, 25);
    }
    return remaining
      .filter(
        p =>
          p.name.toLowerCase().includes(term) ||
          (p.sku || '').toLowerCase().includes(term),
      )
      .slice(0, 25);
  }

  add(product: { id: number; name: string; sku?: string | null }): void {
    this.selected = [
      ...this.selected,
      {
        productId: product.id,
        productName: product.name,
        sku: product.sku,
        qtyPlanned: 1,
      },
    ];
  }

  remove(row: SelectedRow): void {
    this.selected = this.selected.filter(s => s.productId !== row.productId);
  }

  updateQty(row: SelectedRow, value: string | number): void {
    const next = Number(value);
    row.qtyPlanned = Number.isFinite(next) && next > 0 ? Math.floor(next) : 0;
  }

  canSave(): boolean {
    return (
      !this.saving &&
      !!this.destLocation &&
      this.destLocation !== this.sourceLocation &&
      this.selected.length > 0 &&
      this.selected.every(s => s.qtyPlanned > 0)
    );
  }

  save(): void {
    if (!this.canSave()) {
      return;
    }
    this.saving = true;

    const items: StockTransferItemInput[] = this.selected.map(s => ({
      product_id: s.productId,
      qty_planned: s.qtyPlanned,
    }));

    const payload: StockTransferCreateInput = {
      source_location: this.sourceLocation,
      dest_location: this.destLocation,
      notes: this.notes || null,
      items,
    };

    this.service.create(payload).subscribe({
      next: created => {
        this.saving = false;
        this.snackBar.open('Transfer created', 'Close', { duration: 3000 });
        this.dialogRef.close(created);
      },
      error: err => {
        console.error('Failed to create transfer', err);
        this.saving = false;
        // HttpErrorInterceptor surfaces the localized backend message.
      },
    });
  }

  cancel(): void {
    this.dialogRef.close();
  }
}
