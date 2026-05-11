import { Component, Inject, OnInit, OnDestroy, Optional } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule } from '@ngneat/transloco';

import { SuppliersService, PoIngestionResponse, ExtractedLineItem, DocumentParseResult, SupplierDocumentImportReview } from '../../suppliers.service';
import { Supplier } from '../../../shared/models/supplier.model';
import { Product } from '../../../products/models/product.model';
import { ProductService } from '../../../products/services/product';
import { SettingsService } from '../../../core/services/settings.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

export interface PoIngestDialogResult {
    action: 'created' | 'cancelled';
    purchaseOrder?: any;
}

@Component({
    selector: 'app-po-ingest-dialog',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        MatDialogModule,
        MatButtonModule,
        MatIconModule,
        MatTableModule,
        MatFormFieldModule,
        MatInputModule,
        MatSelectModule,
        MatProgressBarModule,
        MatChipsModule,
        MatTooltipModule,
        TranslocoModule,
    ],
    templateUrl: './po-ingest-dialog.component.html',
    styleUrls: ['./po-ingest-dialog.component.scss']
})
export class PoIngestDialogComponent implements OnInit, OnDestroy {
    // State machine
    step: 'upload' | 'preview' | 'creating' = 'upload';
    aiEnabled = false;
    private destroy$ = new Subject<void>();

    // Upload state
    selectedFile: File | null = null;
    isDragging = false;
    uploadError: string | null = null;
    isProcessing = false;

    // Preview state
    extractedData: PoIngestionResponse | null = null;
    editableItems: ExtractedLineItem[] = [];
    displayedColumns = ['sku', 'product', 'description', 'quantity', 'unit_cost', 'line_total', 'actions'];
    importReviewId: number | null = null;
    importedFileName = '';
    reviewWarnings: string[] = [];

    // Form fields for header
    supplierName = '';
    supplierId: number | null = null;
    poNumber = '';
    currency = 'USD';
    shippingCost = 0;
    taxAmount = 0;
    notes = '';

    // Supplier lookup
    suppliers: Supplier[] = [];
    products: Product[] = [];

    constructor(
        private dialogRef: MatDialogRef<PoIngestDialogComponent, PoIngestDialogResult>,
        private suppliersService: SuppliersService,
        private productService: ProductService,
        private settingsService: SettingsService,
        @Optional() @Inject(MAT_DIALOG_DATA) private data?: { review?: SupplierDocumentImportReview }
    ) { }

    ngOnInit(): void {
        this.loadSuppliers();
        this.loadProducts();

        // Check if AI is enabled
        this.settingsService.storeSettings$.pipe(takeUntil(this.destroy$)).subscribe(settings => {
            this.aiEnabled = settings?.ai_config?.enabled || false;
        });

        if (this.data?.review) {
            this.loadImportReview(this.data.review);
        }
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }

    loadSuppliers(): void {
        this.suppliersService.getSuppliers(0, 500).subscribe({
            next: (suppliers) => {
                this.suppliers = suppliers;
                this.matchDetectedSupplier();
            },
            error: (err) => console.error('Failed to load suppliers', err)
        });
    }

    loadProducts(): void {
        this.productService.getProducts(1, 500).subscribe({
            next: (response) => this.products = response.data,
            error: (err: Error) => console.error('Failed to load products', err)
        });
    }

    // --- Drag & Drop ---
    onDragOver(event: DragEvent): void {
        event.preventDefault();
        event.stopPropagation();
        this.isDragging = true;
    }

    onDragLeave(event: DragEvent): void {
        event.preventDefault();
        event.stopPropagation();
        this.isDragging = false;
    }

    onDrop(event: DragEvent): void {
        event.preventDefault();
        event.stopPropagation();
        this.isDragging = false;

        const files = event.dataTransfer?.files;
        if (files && files.length > 0) {
            this.selectFile(files[0]);
        }
    }

    onFileSelected(event: Event): void {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files.length > 0) {
            this.selectFile(input.files[0]);
        }
    }

    selectFile(file: File): void {
        const allowedTypes = ['.pdf', '.png', '.jpg', '.jpeg', '.avif', '.html', '.htm', '.txt'];
        const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();

        if (!allowedTypes.includes(ext)) {
            this.uploadError = `Unsupported file type. Allowed: ${allowedTypes.join(', ')}`;
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            this.uploadError = 'File too large. Maximum 10MB.';
            return;
        }

        this.selectedFile = file;
        this.uploadError = null;
    }

    processFile(): void {
        if (!this.selectedFile) return;

        this.isProcessing = true;
        this.uploadError = null;

        this.suppliersService.createImportReview(this.selectedFile).subscribe({
            next: (review) => {
                const response = review.extracted_data;
                if (response.mode === 'match' && response.matched_po_id) {
                    this.uploadError = `This document appears to match existing ${response.matched_po_number}. Open that PO to receive stock instead.`;
                    this.isProcessing = false;
                    return;
                }

                this.importReviewId = review.id;
                this.importedFileName = review.file_name;
                this.reviewWarnings = review.warnings || [];
                const normalized = this.toPoIngestionResponse(response);
                this.extractedData = normalized;
                this.populateFormFromExtraction(normalized);
                this.step = 'preview';
                this.isProcessing = false;
            },
            error: (err) => {
                this.uploadError = err.error?.detail || 'Failed to process file. Please try again.';
                this.isProcessing = false;
            }
        });
    }

    private loadImportReview(review: SupplierDocumentImportReview): void {
        this.importReviewId = review.id;
        this.importedFileName = review.file_name;
        this.reviewWarnings = review.warnings || [];
        this.supplierId = review.supplier_id;
        const normalized = this.toPoIngestionResponse(review.extracted_data);
        this.extractedData = normalized;
        this.populateFormFromExtraction(normalized);
        this.step = 'preview';
    }

    private toPoIngestionResponse(data: DocumentParseResult): PoIngestionResponse {
        return {
            supplier_name: data.vendor_name,
            po_number: data.po_number,
            po_date: data.document_date,
            currency: data.currency,
            payment_terms: null,
            items: data.items.map(item => ({
                sku: item.sku,
                description: item.description,
                quantity: item.quantity,
                unit_cost: item.unit_cost,
                line_total: item.line_total,
                matched_product_id: item.matched_product_id,
                matched_variant_id: item.matched_variant_id
            })),
            subtotal: data.subtotal,
            shipping_cost: data.shipping_cost,
            tax_amount: data.tax_amount,
            total_amount: data.total_amount,
            extraction_method: 'document-parser',
            confidence_score: data.confidence,
            warnings: []
        };
    }

    populateFormFromExtraction(data: PoIngestionResponse): void {
        this.supplierName = data.supplier_name || '';
        this.poNumber = data.po_number || '';
        this.currency = data.currency || 'USD';
        this.shippingCost = data.shipping_cost || 0;
        this.taxAmount = data.tax_amount || 0;
        this.editableItems = [...data.items];
        this.matchDetectedSupplier();
    }

    private matchDetectedSupplier(): void {
        if (this.supplierId || !this.supplierName || this.suppliers.length === 0) {
            return;
        }

        const detectedName = this.supplierName.toLowerCase();
        const match = this.suppliers.find(s =>
            s.name.toLowerCase().includes(detectedName) ||
            detectedName.includes(s.name.toLowerCase())
        );
        if (match) {
            this.supplierId = match.id;
        }
    }

    // --- Preview Actions ---
    removeItem(index: number): void {
        this.editableItems.splice(index, 1);
    }

    getConfidenceLabel(): string {
        if (!this.extractedData) return '';
        const score = this.extractedData.confidence_score;
        if (score >= 0.7) return 'High';
        if (score >= 0.4) return 'Medium';
        return 'Low';
    }

    getConfidenceColor(): string {
        if (!this.extractedData) return 'accent';
        const score = this.extractedData.confidence_score;
        if (score >= 0.7) return 'primary';
        if (score >= 0.4) return 'accent';
        return 'warn';
    }

    // --- Create PO ---
    createPurchaseOrder(): void {
        if (!this.supplierId) {
            this.uploadError = 'Please select a supplier before creating the PO.';
            return;
        }

        // Filter to only items with matched products
        const matchedItems = this.editableItems.filter(
            item => item.quantity > 0 && item.matched_product_id && item.matched_product_id > 0
        );

        // Warn if some items won't be included
        const unmatchedCount = this.editableItems.length - matchedItems.length;
        if (matchedItems.length === 0) {
            this.uploadError = 'No items have been matched to existing products. Please match items to products first.';
            return;
        }

        this.step = 'creating';

        if (!this.importReviewId) {
            this.uploadError = 'Please process or select an import review before approving.';
            this.step = 'preview';
            return;
        }

        const approval = {
            supplier_id: this.supplierId,
            currency: this.currency,
            notes: this.notes || `Imported from ${this.importedFileName || this.selectedFile?.name || 'document'}${unmatchedCount > 0 ? ` (${unmatchedCount} unmatched items excluded)` : ''}`,
            shipping_cost: this.shippingCost,
            tax_amount: this.taxAmount,
            items: matchedItems
        };

        this.suppliersService.approveImportReview(this.importReviewId, approval).subscribe({
            next: (response) => {
                this.dialogRef.close({ action: 'created', purchaseOrder: response.purchase_order });
            },
            error: (err) => {
                this.uploadError = err.error?.detail || 'Failed to create Purchase Order.';
                this.step = 'preview';
            }
        });
    }

    cancel(): void {
        this.dialogRef.close({ action: 'cancelled' });
    }

    goBack(): void {
        this.step = 'upload';
        this.extractedData = null;
    }
}
