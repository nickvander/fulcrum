import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { finalize } from 'rxjs';

import {
  Payment,
  PaymentsService,
  PaymentStatus,
} from '../../services/payments.service';
import {
  PaymentDetailDialogComponent,
  PaymentDetailDialogData,
} from '../payment-detail-dialog/payment-detail-dialog.component';

const ALL_STATUSES: (PaymentStatus | 'all')[] = [
  'all', 'pending', 'approved', 'rejected', 'refunded', 'cancelled',
];

@Component({
  selector: 'app-payments-page',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSnackBarModule,
    MatTableModule,
    MatTooltipModule,
    TranslocoModule,
  ],
  templateUrl: './payments-page.component.html',
  styleUrls: ['./payments-page.component.scss'],
})
export class PaymentsPageComponent implements OnInit {
  payments: Payment[] = [];
  total = 0;
  loading = false;
  selectedStatus: PaymentStatus | 'all' = 'all';
  pageSize = 25;
  pageIndex = 0;
  readonly statusOptions = ALL_STATUSES;
  readonly pageSizeOptions = [10, 25, 50, 100];

  readonly displayedColumns = [
    'id', 'created_at', 'status', 'amount', 'payer_email',
    'external_payment_id', 'sales_order_id', 'actions',
  ];

  constructor(
    private paymentsService: PaymentsService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private transloco: TranslocoService,
  ) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading = true;
    const status = this.selectedStatus === 'all' ? null : this.selectedStatus;
    this.paymentsService.list({
      status,
      skip: this.pageIndex * this.pageSize,
      limit: this.pageSize,
    })
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: (res) => {
          this.payments = res.items;
          this.total = res.total;
        },
        error: () => this.snack('payments.errors.loadFailed'),
      });
  }

  onStatusChange(): void {
    // Reset pagination when the filter changes — otherwise the user can
    // land on a page that no longer exists for the new filter.
    this.pageIndex = 0;
    this.refresh();
  }

  onPage(event: PageEvent): void {
    this.pageIndex = event.pageIndex;
    this.pageSize = event.pageSize;
    this.refresh();
  }

  openDetail(payment: Payment): void {
    this.dialog.open<PaymentDetailDialogComponent, PaymentDetailDialogData, void>(
      PaymentDetailDialogComponent,
      {
        data: { payment },
        width: '720px',
        maxHeight: '90vh',
      },
    );
  }

  formatTimestamp(iso: string | null | undefined): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleString();
  }

  formatAmount(payment: Payment): string {
    return `${payment.amount.toFixed(2)} ${payment.currency}`;
  }

  statusClass(status: string): string {
    return `status-${status}`;
  }

  private snack(key: string): void {
    this.snackBar.open(
      this.transloco.translate(key),
      this.transloco.translate('common.close'),
      { duration: 4000 },
    );
  }
}
