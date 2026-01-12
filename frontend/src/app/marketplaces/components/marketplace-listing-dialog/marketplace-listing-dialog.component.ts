import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule } from '@ngneat/transloco';
import { AiService, ListingDescriptionResponse } from '../../../core/services/ai.service';
import { NotificationService } from '../../../core/services/notification.service';
import { SettingsService, StoreSettings } from '../../../core/services/settings.service';
import { MarketplacesService, MarketplaceListingCreate } from '../../marketplaces';
import { switchMap } from 'rxjs/operators';
import { of } from 'rxjs';

export interface MarketplaceListingDialogData {
    productId: number;
    productName: string;
    marketplace: string;
    existingTitle?: string;
    existingDescription?: string;
}

@Component({
    selector: 'app-marketplace-listing-dialog',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        ReactiveFormsModule,
        MatDialogModule,
        MatButtonModule,
        MatFormFieldModule,
        MatInputModule,
        MatSelectModule,
        MatProgressSpinnerModule,
        MatIconModule,
        MatChipsModule,
        MatTooltipModule,
        TranslocoModule
    ],
    templateUrl: './marketplace-listing-dialog.component.html',
    styleUrl: './marketplace-listing-dialog.component.scss'
})
export class MarketplaceListingDialogComponent implements OnInit {
    listingForm: FormGroup;
    isGenerating = false;
    isSaving = false;
    generatedKeywords: string[] = [];
    aiEnabled = false;

    availableMarketplaces = [
        { value: 'amazon', label: 'Amazon' },
        { value: 'mercadolibre', label: 'MercadoLibre' },
        { value: 'ebay', label: 'eBay' }
    ];

    constructor(
        private fb: FormBuilder,
        private dialogRef: MatDialogRef<MarketplaceListingDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: MarketplaceListingDialogData,
        private aiService: AiService,
        private notificationService: NotificationService,
        private settingsService: SettingsService,
        private marketplacesService: MarketplacesService
    ) {
        this.listingForm = this.fb.group({
            marketplace: [data.marketplace || 'amazon', Validators.required],
            title: [data.existingTitle || data.productName || '', Validators.required],
            description: [data.existingDescription || '', Validators.required]
        });
    }

    ngOnInit(): void {
        // Check if AI is enabled in settings
        this.settingsService.getStoreSettings().subscribe({
            next: (settings: StoreSettings | null) => {
                this.aiEnabled = settings?.ai_config?.enabled || false;
            },
            error: () => {
                this.aiEnabled = false;
            }
        });
    }

    generateWithAI(): void {
        this.isGenerating = true;
        const marketplace = this.listingForm.get('marketplace')?.value;

        this.aiService.generateListingDescription({
            product_id: this.data.productId,
            marketplace_name: marketplace,
            include_title: true,
            include_keywords: true
        }).subscribe({
            next: (response: ListingDescriptionResponse) => {
                this.isGenerating = false;
                if (response.error) {
                    this.notificationService.showError(response.error);
                    return;
                }

                // Update form with generated content
                if (response.title) {
                    this.listingForm.patchValue({ title: response.title });
                }
                if (response.description) {
                    this.listingForm.patchValue({ description: response.description });
                }
                if (response.keywords && response.keywords.length > 0) {
                    this.generatedKeywords = response.keywords;
                }

                this.notificationService.showSuccess('AI generated listing content successfully!');
            },
            error: (err) => {
                this.isGenerating = false;
                this.notificationService.showError('Failed to generate content: ' + (err.message || 'Unknown error'));
            }
        });
    }

    copyKeywords(): void {
        if (this.generatedKeywords.length === 0) return;
        const keywordsString = this.generatedKeywords.join(', ');
        navigator.clipboard.writeText(keywordsString).then(() => {
            this.notificationService.showSuccess('Keywords copied to clipboard!');
        }).catch(() => {
            this.notificationService.showError('Failed to copy keywords');
        });
    }

    onSave(): void {
        if (!this.listingForm.valid) return;

        this.isSaving = true;
        const formValue = this.listingForm.value;
        const marketplaceName = formValue.marketplace;

        // First, get or create the marketplace to get its ID
        this.marketplacesService.getMarketplaceByName(marketplaceName).pipe(
            switchMap(marketplace => {
                if (!marketplace) {
                    // Create the marketplace if it doesn't exist
                    return this.marketplacesService.createMarketplace({
                        name: marketplaceName.charAt(0).toUpperCase() + marketplaceName.slice(1),
                        api_base_url: ''
                    });
                }
                return of(marketplace);
            }),
            switchMap(marketplace => {
                // Create the listing with metadata
                const listingCreate: MarketplaceListingCreate = {
                    product_id: this.data.productId,
                    marketplace_id: marketplace.id,
                    status: 'draft',
                    sync_status: 'PENDING',
                    metadata_json: {
                        title: formValue.title,
                        description: formValue.description,
                        keywords: this.generatedKeywords
                    }
                };
                return this.marketplacesService.createListing(listingCreate);
            })
        ).subscribe({
            next: (listing) => {
                this.isSaving = false;
                this.notificationService.showSuccess('Listing saved successfully!');
                this.dialogRef.close(listing);
            },
            error: (err) => {
                this.isSaving = false;
                this.notificationService.showError('Failed to save listing: ' + (err.error?.detail || err.message || 'Unknown error'));
            }
        });
    }

    onCancel(): void {
        this.dialogRef.close();
    }
}
