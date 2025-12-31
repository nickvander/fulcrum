import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { FormsModule } from '@angular/forms';
import {
    IntegrationsService,
    PendingBatchInfo,
    PendingChangeInfo
} from '../../services/integrations.service';
import { NotificationService } from '../../../core/services/notification.service';

@Component({
    selector: 'app-pending-sync-dialog',
    templateUrl: './pending-sync-dialog.html',
    styleUrl: './pending-sync-dialog.scss',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        MatDialogModule,
        MatButtonModule,
        MatIconModule,
        MatCheckboxModule,
        MatProgressBarModule,
        MatTooltipModule,
    ]
})
export class PendingSyncDialog implements OnInit {
    batches: PendingBatchInfo[] = [];
    loading = true;
    processing = false;

    // Track selected changes per batch
    selectedChanges: Map<number, Set<number>> = new Map();

    constructor(
        private dialogRef: MatDialogRef<PendingSyncDialog>,
        private integrationsService: IntegrationsService,
        private notificationService: NotificationService
    ) { }

    ngOnInit(): void {
        this.loadPendingBatches();
    }

    loadPendingBatches(): void {
        this.loading = true;
        this.integrationsService.getPendingBatches().subscribe({
            next: (response) => {
                this.batches = response.batches;
                // Initialize selection state
                this.batches.forEach(batch => {
                    this.selectedChanges.set(batch.id, new Set());
                });
                this.loading = false;
            },
            error: (err) => {
                console.error('Failed to load pending batches', err);
                this.loading = false;
            }
        });
    }

    isChangeSelected(batchId: number, changeId: number): boolean {
        return this.selectedChanges.get(batchId)?.has(changeId) ?? false;
    }

    toggleChange(batchId: number, changeId: number): void {
        const selected = this.selectedChanges.get(batchId);
        if (!selected) return;

        if (selected.has(changeId)) {
            selected.delete(changeId);
        } else {
            selected.add(changeId);
        }
    }

    selectAll(batch: PendingBatchInfo): void {
        const selected = this.selectedChanges.get(batch.id);
        if (!selected) return;
        batch.changes.forEach(c => selected.add(c.id));
    }

    deselectAll(batch: PendingBatchInfo): void {
        this.selectedChanges.set(batch.id, new Set());
    }

    getSelectedCount(batchId: number): number {
        return this.selectedChanges.get(batchId)?.size ?? 0;
    }

    getTotalChanges(): number {
        return this.batches.reduce((sum, b) => sum + b.changes.length, 0);
    }

    approveSelected(batch: PendingBatchInfo): void {
        const changeIds = Array.from(this.selectedChanges.get(batch.id) ?? []);
        if (changeIds.length === 0) {
            this.notificationService.showError('Select at least one change to approve');
            return;
        }

        this.processing = true;
        this.integrationsService.approveSyncChanges(batch.id, changeIds).subscribe({
            next: (response) => {
                this.notificationService.showSuccess(response.message);
                this.processing = false;
                this.loadPendingBatches();
            },
            error: (err) => {
                this.notificationService.showError('Failed to approve changes');
                this.processing = false;
            }
        });
    }

    rejectSelected(batch: PendingBatchInfo): void {
        const changeIds = Array.from(this.selectedChanges.get(batch.id) ?? []);
        if (changeIds.length === 0) {
            this.notificationService.showError('Select at least one change to reject');
            return;
        }

        this.processing = true;
        this.integrationsService.rejectSyncChanges(batch.id, changeIds).subscribe({
            next: (response) => {
                this.notificationService.showSuccess(response.message);
                this.processing = false;
                this.loadPendingBatches();
            },
            error: (err) => {
                this.notificationService.showError('Failed to reject changes');
                this.processing = false;
            }
        });
    }

    approveAll(batch: PendingBatchInfo): void {
        const changeIds = batch.changes.map(c => c.id);
        this.processing = true;
        this.integrationsService.approveSyncChanges(batch.id, changeIds).subscribe({
            next: (response) => {
                this.notificationService.showSuccess(response.message);
                this.processing = false;
                this.loadPendingBatches();
            },
            error: (err) => {
                this.notificationService.showError('Failed to approve changes');
                this.processing = false;
            }
        });
    }

    rejectAll(batch: PendingBatchInfo): void {
        const changeIds = batch.changes.map(c => c.id);
        this.processing = true;
        this.integrationsService.rejectSyncChanges(batch.id, changeIds).subscribe({
            next: (response) => {
                this.notificationService.showSuccess(response.message);
                this.processing = false;
                this.loadPendingBatches();
            },
            error: (err) => {
                this.notificationService.showError('Failed to reject changes');
                this.processing = false;
            }
        });
    }

    formatValue(value: string | null, field: string): string {
        if (value === null || value === '') return '—';
        if (field.includes('price') || field.includes('cost')) {
            const num = parseFloat(value);
            return isNaN(num) ? value : `$${num.toFixed(2)}`;
        }
        return value;
    }

    getFieldIcon(field: string): string {
        switch (field) {
            case 'cost_price': return 'payments';
            case 'resale_price': return 'sell';
            case 'name': return 'label';
            case 'stock': return 'inventory';
            default: return 'edit';
        }
    }

    getSourceLabel(source: string): string {
        switch (source) {
            case 'google_sheets': return 'Google Sheets';
            case 'csv_import': return 'CSV Import';
            default: return source;
        }
    }

    close(): void {
        this.dialogRef.close();
    }
}
