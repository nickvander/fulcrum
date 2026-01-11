import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
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

import { SuppliersService, PoIngestionResponse, ExtractedLineItem } from '../../suppliers.service';
import { PurchaseOrderCreate, PurchaseOrderStatus } from '../../../shared/models/purchase-order.model';
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
        private settingsService: SettingsService
    ) { }

    ngOnInit(): void {
        this.loadSuppliers();
        this.loadProducts();

        // Check if AI is enabled
        this.settingsService.storeSettings$.pipe(takeUntil(this.destroy$)).subscribe(settings => {
            this.aiEnabled = settings?.ai_config?.enabled || false;
        });
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }

    loadSuppliers(): void {
        this.suppliersService.getSuppliers(0, 500).subscribe({
            next: (suppliers) => this.suppliers = suppliers,
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
        const allowedTypes = ['.pdf', '.html', '.htm', '.txt'];
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

        this.suppliersService.ingestPurchaseOrder(this.selectedFile, false).subscribe({
            next: (response) => {
                this.extractedData = response;
                this.populateFormFromExtraction(response);
                this.step = 'preview';
                this.isProcessing = false;
            },
            error: (err) => {
                this.uploadError = err.error?.detail || 'Failed to process file. Please try again.';
                this.isProcessing = false;
            }
        });
    }

    populateFormFromExtraction(data: PoIngestionResponse): void {
        this.supplierName = data.supplier_name || '';
        this.poNumber = data.po_number || '';
        this.currency = data.currency || 'USD';
        this.shippingCost = data.shipping_cost || 0;
        this.taxAmount = data.tax_amount || 0;
        this.editableItems = [...data.items];

        // Try to match supplier
        if (data.supplier_name) {
            const match = this.suppliers.find(s =>
                s.name.toLowerCase().includes(data.supplier_name!.toLowerCase()) ||
                data.supplier_name!.toLowerCase().includes(s.name.toLowerCase())
            );
            if (match) {
                this.supplierId = match.id;
            }
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

        const poData: PurchaseOrderCreate = {
            supplier_id: this.supplierId,
            status: PurchaseOrderStatus.DRAFT,
            currency: this.currency,
            notes: this.notes || `Imported from ${this.selectedFile?.name || 'document'}${unmatchedCount > 0 ? ` (${unmatchedCount} unmatched items excluded)` : ''}`,
            shipping_cost: this.shippingCost,
            tax_amount: this.taxAmount,
            items: matchedItems.map(item => ({
                product_id: item.matched_product_id!,
                quantity_ordered: item.quantity,
                unit_cost: item.unit_cost
            }))
        };

        this.suppliersService.createPurchaseOrder(poData).subscribe({
            next: (po) => {
                this.dialogRef.close({ action: 'created', purchaseOrder: po });
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
