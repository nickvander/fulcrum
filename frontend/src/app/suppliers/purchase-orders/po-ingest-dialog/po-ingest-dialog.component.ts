import { Component, Inject, OnInit, OnDestroy, Optional } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';

import { SuppliersService, PoIngestionResponse, ExtractedLineItem, DocumentParseResult, SupplierDocumentImportReview } from '../../suppliers.service';
import { translateApiError } from '../../../core/errors/translate-api-error';
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

interface MatchDiffLine {
    po_item_id: number | null;
    po_description: string | null;
    po_quantity: number | null;
    po_remaining_quantity: number | null;
    po_unit_cost: number | null;
    invoice_sku: string | null;
    invoice_description: string;
    invoice_quantity: number;
    invoice_unit_cost: number;
    match_status: 'matched' | 'quantity_diff' | 'price_diff' | 'unmatched' | string;
    discrepancy_details: string | null;
}

interface MatchDiffUnmatchedItem {
    description?: string;
    sku?: string;
    quantity?: number;
    unit_cost?: number;
    [k: string]: unknown;
}

interface MatchDiffDetails {
    matches: MatchDiffLine[];
    unmatched_po_items: MatchDiffUnmatchedItem[];
    unmatched_invoice_items: MatchDiffUnmatchedItem[];
    total_discrepancy: number;
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
        MatSnackBarModule,
        TranslocoModule,
    ],
    templateUrl: './po-ingest-dialog.component.html',
    styleUrls: ['./po-ingest-dialog.component.scss']
})
export class PoIngestDialogComponent implements OnInit, OnDestroy {
    // State machine
    step: 'upload' | 'preview' | 'match-diff' | 'creating' = 'upload';
    aiEnabled = false;
    private destroy$ = new Subject<void>();

    // Upload state
    selectedFile: File | null = null;
    isDragging = false;
    uploadError: string | null = null;
    isProcessing = false;

    // Match-diff state (populated when the uploaded document matches an existing PO).
    // The shape mirrors InvoiceMatchResult on the backend (see purchase_orders.py).
    matchedPoId: number | null = null;
    matchedPoNumber: string | null = null;
    matchedSupplierName: string | null = null;
    matchedInvoiceNumber: string | null = null;
    matchedInvoiceDate: string | null = null;
    matchDetails: MatchDiffDetails | null = null;

    // Preview state
    extractedData: PoIngestionResponse | null = null;
    editableItems: ExtractedLineItem[] = [];
    displayedColumns = ['sku', 'product', 'description', 'quantity', 'unit_cost', 'line_total', 'actions'];
    importReviewId: number | null = null;
    importedFileName = '';
    reviewWarnings: string[] = [];
    assistingItemIndex: number | null = null;

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
        private snackBar: MatSnackBar,
        private transloco: TranslocoService,
        private router: Router,
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
                this.importReviewId = review.id;
                this.importedFileName = review.file_name;
                this.reviewWarnings = review.warnings || [];

                if (response.mode === 'match' && response.matched_po_id) {
                    // Don't kick the user out of the dialog like the old
                    // behaviour did — render a side-by-side diff against the
                    // existing PO so they can see qty/price deltas inline.
                    this.matchedPoId = response.matched_po_id;
                    this.matchedPoNumber = response.matched_po_number ?? null;
                    this.matchedSupplierName = response.matched_supplier_name ?? null;
                    this.matchedInvoiceNumber = response.invoice_number ?? null;
                    this.matchedInvoiceDate = response.document_date ?? null;
                    this.matchDetails = {
                        matches: (response.matches as MatchDiffLine[]) ?? [],
                        unmatched_po_items: (response.unmatched_po_items as MatchDiffUnmatchedItem[]) ?? [],
                        unmatched_invoice_items: (response.unmatched_invoice_items as MatchDiffUnmatchedItem[]) ?? [],
                        total_discrepancy: response.total_discrepancy ?? 0,
                    };
                    this.step = 'match-diff';
                    this.isProcessing = false;
                    return;
                }

                const normalized = this.toPoIngestionResponse(response);
                this.extractedData = normalized;
                this.populateFormFromExtraction(normalized);
                this.step = 'preview';
                this.isProcessing = false;
            },
            error: (err) => {
                this.uploadError = translateApiError(err, this.transloco, 'purchaseOrders.ingestErrors.processFailed');
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

    createProductForItem(item: ExtractedLineItem, index: number): void {
        if (!this.importReviewId) {
            this.uploadError = 'Please process or select an import review before creating products.';
            return;
        }
        if (!this.supplierId) {
            this.uploadError = 'Please select a supplier before creating a product from this line.';
            return;
        }

        this.assistingItemIndex = index;
        this.uploadError = null;
        this.suppliersService.createProductFromImportReviewItem(
            this.importReviewId,
            index,
            {
                supplier_id: this.supplierId,
                name: item.description || item.sku || 'Imported product',
                sku: item.sku,
                default_resale_price: item.unit_cost || 0,
                create_alias: true
            }
        ).subscribe({
            next: (response) => {
                if (response.product && !this.products.some(product => product.id === response.product!.id)) {
                    this.products = [...this.products, response.product];
                }
                this.applyAssistedReview(response.import_review);
                this.snackBar.open('Product created and matched to this line', 'Close', { duration: 3000 });
                this.assistingItemIndex = null;
            },
            error: (err) => {
                this.uploadError = translateApiError(err, this.transloco, 'purchaseOrders.ingestErrors.productCreateFailed');
                this.assistingItemIndex = null;
            }
        });
    }

    learnAliasForItem(item: ExtractedLineItem, index: number): void {
        if (!this.importReviewId) {
            this.uploadError = 'Please process or select an import review before learning aliases.';
            return;
        }
        if (!this.supplierId) {
            this.uploadError = 'Please select a supplier before learning an alias.';
            return;
        }
        if (!item.matched_product_id) {
            this.uploadError = 'Select a Fulcrum product before learning this alias.';
            return;
        }

        this.assistingItemIndex = index;
        this.uploadError = null;
        this.suppliersService.learnAliasFromImportReviewItem(
            this.importReviewId,
            index,
            {
                supplier_id: this.supplierId,
                product_id: item.matched_product_id,
                variant_id: item.matched_variant_id || null,
                alias_sku: item.sku,
                alias_name: item.description
            }
        ).subscribe({
            next: (response) => {
                this.applyAssistedReview(response.import_review);
                this.snackBar.open('Supplier alias learned for this line', 'Close', { duration: 3000 });
                this.assistingItemIndex = null;
            },
            error: (err) => {
                this.uploadError = translateApiError(err, this.transloco, 'purchaseOrders.ingestErrors.aliasLearnFailed');
                this.assistingItemIndex = null;
            }
        });
    }

    getProductLabel(productId: number | null | undefined): string {
        if (!productId) return '';
        const product = this.products.find(item => item.id === productId);
        return product ? `${product.sku} - ${product.name}` : `Product #${productId}`;
    }

    private applyAssistedReview(review: SupplierDocumentImportReview): void {
        this.importReviewId = review.id;
        this.reviewWarnings = review.warnings || [];
        this.supplierId = review.supplier_id || this.supplierId;
        const normalized = this.toPoIngestionResponse(review.extracted_data);
        this.extractedData = normalized;
        this.editableItems = [...normalized.items];
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
                this.uploadError = translateApiError(err, this.transloco, 'purchaseOrders.ingestErrors.poCreateFailed');
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
        this.matchedPoId = null;
        this.matchedPoNumber = null;
        this.matchedSupplierName = null;
        this.matchedInvoiceNumber = null;
        this.matchedInvoiceDate = null;
        this.matchDetails = null;
    }

    /**
     * Close the dialog and navigate to the existing PO this document
     * matched. From there the user can use the PO's own invoice-receive
     * flow to apply qty/price adjustments based on what they saw in the
     * diff.
     */
    openMatchedPo(): void {
        if (!this.matchedPoId) return;
        this.dialogRef.close({ action: 'cancelled' });
        this.router.navigate(['/suppliers/po', this.matchedPoId, 'edit']);
    }

    /**
     * Reject the matched-PO import without creating anything — used when
     * the diff makes it clear that the document doesn't actually belong
     * to this PO (e.g. wrong supplier picked up by a fuzzy match).
     */
    rejectMatchedImport(): void {
        if (!this.importReviewId) {
            this.cancel();
            return;
        }
        this.suppliersService.rejectImportReview(this.importReviewId).subscribe({
            next: () => {
                this.snackBar.open(
                    this.transloco.translate('purchaseOrders.matchDiff.rejected'),
                    this.transloco.translate('common.close'),
                    { duration: 4000 },
                );
                this.dialogRef.close({ action: 'cancelled' });
            },
            error: () => {
                // HttpErrorInterceptor surfaces the localized backend message.
            },
        });
    }

    matchStatusClass(status: string): string {
        switch (status) {
            case 'matched': return 'match-ok';
            case 'quantity_diff': return 'match-qty';
            case 'price_diff': return 'match-price';
            case 'unmatched': return 'match-none';
            default: return '';
        }
    }
}
