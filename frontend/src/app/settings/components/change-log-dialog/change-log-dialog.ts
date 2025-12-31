import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { FormsModule } from '@angular/forms';
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
        MatDialogModule,
        MatButtonModule,
        MatIconModule,
        MatProgressBarModule,
        MatSelectModule,
        MatFormFieldModule,
        MatPaginatorModule,
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
        private integrationsService: IntegrationsService
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

    getSourceLabel(source: string): string {
        switch (source) {
            case 'sheets_import': return 'Sheets Import';
            case 'direct_edit': return 'Direct Edit';
            case 'api': return 'API';
            default: return source;
        }
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

    close(): void {
        this.dialogRef.close();
    }
}
