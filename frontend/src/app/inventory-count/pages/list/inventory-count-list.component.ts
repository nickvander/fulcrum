import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { finalize } from 'rxjs';

import {
  InventoryCountService,
  InventoryCountSessionHeader,
  InventoryCountSessionStatus,
} from '../../services/inventory-count.service';


/**
 * Lists physical-count sessions newest first + lets the operator
 * start a new one. The "Start" inputs are inline (no separate
 * dialog) — operator picks a location + optional notes, clicks
 * Start, gets routed straight into the session detail page.
 */
@Component({
  selector: 'app-inventory-count-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSnackBarModule,
    MatTableModule,
    TranslocoModule,
  ],
  templateUrl: './inventory-count-list.component.html',
  styleUrl: './inventory-count-list.component.scss',
})
export class InventoryCountListComponent implements OnInit {
  sessions: InventoryCountSessionHeader[] = [];
  loading = false;
  starting = false;

  /** Status filter. '' = all statuses. */
  statusFilter: '' | InventoryCountSessionStatus = '';
  newLocation = 'default';
  newNotes = '';

  readonly statusOptions: Array<{ value: '' | InventoryCountSessionStatus; labelKey: string }> = [
    { value: '', labelKey: 'inventoryCount.list.statusAll' },
    { value: 'in_progress', labelKey: 'inventoryCount.list.statusInProgress' },
    { value: 'committed', labelKey: 'inventoryCount.list.statusCommitted' },
    { value: 'cancelled', labelKey: 'inventoryCount.list.statusCancelled' },
  ];

  readonly displayedColumns = [
    'started_at', 'status', 'location', 'item_count', 'started_by', 'actions',
  ];

  constructor(
    private countService: InventoryCountService,
    private router: Router,
    private snackBar: MatSnackBar,
    private transloco: TranslocoService,
  ) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading = true;
    this.countService.list({ status: this.statusFilter || null })
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: (rows) => (this.sessions = rows),
        error: () => (this.sessions = []),
      });
  }

  start(): void {
    if (this.starting) return;
    this.starting = true;
    this.countService.start({
      location: this.newLocation || 'default',
      notes: this.newNotes || undefined,
    })
      .pipe(finalize(() => (this.starting = false)))
      .subscribe({
        next: (session) => {
          this.router.navigate(['/inventory/count', session.id]);
        },
        error: () => {
          this.snackBar.open(
            this.transloco.translate('inventoryCount.list.startFailed'),
            this.transloco.translate('common.close'),
            { duration: 4000 },
          );
        },
      });
  }

  statusChipClass(status: string): string {
    if (status === 'in_progress') return 'chip-progress';
    if (status === 'committed') return 'chip-committed';
    return 'chip-cancelled';
  }
}
