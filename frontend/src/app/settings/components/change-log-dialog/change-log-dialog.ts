import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { MaterialModule } from '../../../shared/material.module';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { MatDialogRef } from '@angular/material/dialog';
import { PageEvent } from '@angular/material/paginator';
import {
    IntegrationsService,
    ChangeLogEntry
} from '../../services/integrations.service';

@Component({
    selector: 'app-change-log-dialog',
    templateUrl: './change-log-dialog.html',
    styleUrl: './change-log-dialog.scss',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        MaterialModule,
        TranslocoModule,
        EmptyStateComponent,
        LoadingSpinnerComponent
    ]
})
export class ChangeLogDialog implements OnInit {
    entries: ChangeLogEntry[] = [];
    loading = true;
    total = 0;

    // Filters
    sourceFilter = '';

    // Pagination
    pageSize = 25;
    pageIndex = 0;

    constructor(
        private dialogRef: MatDialogRef<ChangeLogDialog>,
        private integrationsService: IntegrationsService,
        private translocoService: TranslocoService
    ) { }

    ngOnInit(): void {
        this.loadChangeLogs();
    }

    loadChangeLogs(): void {
        this.loading = true;
        const params: any = {
            limit: this.pageSize,
            offset: this.pageIndex * this.pageSize
        };

        if (this.sourceFilter) {
            params.source = this.sourceFilter;
        }

        this.integrationsService.getChangeLogs(params).subscribe({
            next: (response) => {
                this.entries = response.entries;
                this.total = response.total;
                this.loading = false;
            },
            error: (err) => {
                console.error('Failed to load change logs', err);
                this.loading = false;
            }
        });
    }

    onPageChange(event: PageEvent): void {
        this.pageIndex = event.pageIndex;
        this.pageSize = event.pageSize;
        this.loadChangeLogs();
    }

    onSourceFilterChange(): void {
        this.pageIndex = 0;
        this.loadChangeLogs();
    }

    formatValue(value: string | null, field: string): string {
        if (value === null || value === '') return '—';
        if (field.includes('price') || field.includes('cost')) {
            const num = parseFloat(value);
            return isNaN(num) ? value : `$${num.toFixed(2)}`;
        }
        return value;
    }

    getSourceBadgeClass(source: string): string {
        switch (source) {
            case 'sheets_import': return 'badge-sheets';
            case 'direct_edit': return 'badge-direct';
            case 'api': return 'badge-api';
            default: return '';
        }
    }

    // REPLACED getSourceLabel with direct template translation

    getFieldIcon(field: string): string {
        switch (field) {
            case 'cost_price': return 'payments';
            case 'resale_price': return 'sell';
            case 'name': return 'label';
            case 'stock': return 'inventory';
            default: return 'edit';
        }
    }

    getFieldLabelKey(field: string): string {
        switch (field) {
            case 'cost_price': return 'common.cost';
            case 'resale_price': return 'common.price';
            case 'name': return 'common.name';
            case 'stock': return 'common.stock';
            default: return 'settings.changeLog.fields.' + field;
        }
    }

    close(): void {
        this.dialogRef.close();
    }
}
