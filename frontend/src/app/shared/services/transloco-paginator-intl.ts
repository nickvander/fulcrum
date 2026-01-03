import { Injectable } from '@angular/core';
import { MatPaginatorIntl } from '@angular/material/paginator';
import { TranslocoService } from '@ngneat/transloco';
import { Subject } from 'rxjs';
import { take } from 'rxjs/operators';

@Injectable()
export class TranslocoPaginatorIntl extends MatPaginatorIntl {
    override changes = new Subject<void>();

    constructor(private translocoService: TranslocoService) {
        super();

        // Subscribe to language changes
        this.translocoService.langChanges$.subscribe(() => {
            this.updateTranslations();
        });

        // Initial update - wait for translations to be ready
        this.translocoService.selectTranslate('common.pagination.itemsPerPage')
            .pipe(take(1))
            .subscribe(() => {
                this.updateTranslations();
            });
    }

    private updateTranslations(): void {
        this.itemsPerPageLabel = this.translocoService.translate('common.pagination.itemsPerPage');
        this.nextPageLabel = this.translocoService.translate('common.pagination.nextPage');
        this.previousPageLabel = this.translocoService.translate('common.pagination.previousPage');
        this.firstPageLabel = this.translocoService.translate('common.pagination.firstPage');
        this.lastPageLabel = this.translocoService.translate('common.pagination.lastPage');
        this.changes.next();
    }

    override getRangeLabel = (page: number, pageSize: number, length: number): string => {
        if (length === 0 || pageSize === 0) {
            return this.translocoService.translate('common.pagination.rangeEmpty', { total: length });
        }
        const startIndex = page * pageSize;
        const endIndex = Math.min(startIndex + pageSize, length);
        return this.translocoService.translate('common.pagination.range', {
            start: startIndex + 1,
            end: endIndex,
            total: length
        });
    };
}
