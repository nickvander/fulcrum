import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
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
        private notificationService: NotificationService,
        private transloco: TranslocoService
    ) { }

    exportData(entity: string, format: 'csv' | 'json'): void {
        const filename = `${entity.replace('-', '_')}_export.${format}`;
        this.integrationsService.exportEntity(entity, format).subscribe({
            next: (blob) => {
                this.integrationsService.downloadBlob(blob, filename);
                this.notificationService.showSuccess(
                    this.transloco.translate('settings.dataTab.exportSuccess', { entity: entity.replace('-', ' ') })
                );
            },
            error: (err) => {
                console.error('Export failed', err);
                this.notificationService.showError(
                    this.transloco.translate('notifications.exportFailed')
                );
            }
        });
    }
}
