import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslocoModule } from '@ngneat/transloco';
import { MaterialModule } from '../../../shared/material.module';
import { IntegrationsService } from '../../services/integrations.service';
import { NotificationService } from '../../../core/services/notification.service';

@Component({
    selector: 'app-data-tab',
    standalone: true,
    imports: [CommonModule, TranslocoModule, MaterialModule],
    templateUrl: './data-tab.component.html',
    styleUrls: ['./data-tab.component.scss']
})
export class DataTabComponent {
    constructor(
        private integrationsService: IntegrationsService,
        private notificationService: NotificationService
    ) { }

    exportData(entity: string, format: 'csv' | 'json'): void {
        const filename = `${entity.replace('-', '_')}_export.${format}`;
        this.integrationsService.exportEntity(entity, format).subscribe({
            next: (blob) => {
                this.integrationsService.downloadBlob(blob, filename);
                this.notificationService.showSuccess(`${entity.replace('-', ' ')} exported successfully!`);
            },
            error: (err) => {
                console.error('Export failed', err);
                this.notificationService.showError('Export failed. Please try again.');
            }
        });
    }
}
