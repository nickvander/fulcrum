import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { TranslocoModule } from '@ngneat/transloco';
import { MaterialModule } from '../../../shared/material.module';
import { SettingsService } from '../../../core/services/settings.service';
import { NotificationService } from '../../../core/services/notification.service';

@Component({
    selector: 'app-inventory-tab',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, TranslocoModule, MaterialModule],
    templateUrl: './inventory-tab.component.html',
    styleUrls: ['./inventory-tab.component.scss']
})
export class InventoryTabComponent implements OnInit {
    form: FormGroup;

    constructor(
        private fb: FormBuilder,
        private settingsService: SettingsService,
        private notificationService: NotificationService
    ) {
        this.form = this.fb.group({
            low_inventory_days_default: [30, [Validators.required, Validators.min(1)]],
            low_stock_quantity_default: [10, [Validators.required, Validators.min(0)]]
        });
    }

    ngOnInit(): void {
        this.settingsService.storeSettings$.subscribe(storeSettings => {
            if (storeSettings) {
                this.form.patchValue(storeSettings, { emitEvent: false });
            }
        });
    }

    onSubmit(): void {
        if (this.form.valid) {
            this.settingsService.updateStoreSettings(this.form.value).subscribe({
                next: () => this.notificationService.showSuccess('Store Settings saved successfully!'),
                error: (err) => this.notificationService.showError('Failed to save store settings')
            });
        }
    }
}
