import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of } from 'rxjs';
import { vi } from 'vitest';

import { ProductService } from '../../../products/services/product';
import { SettingsService } from '../../../core/services/settings.service';
import { SuppliersService } from '../../suppliers.service';
import { PoIngestDialogComponent } from './po-ingest-dialog.component';

describe('PoIngestDialogComponent', () => {
    let component: PoIngestDialogComponent;
    let fixture: ComponentFixture<PoIngestDialogComponent>;
    let suppliersServiceMock: any;
    let productServiceMock: any;
    let dialogRefMock: any;
    let snackBarMock: any;

    const baseReview: any = {
        id: 42,
        file_name: 'alibaba.txt',
        content_type: 'text/plain',
        source: 'supplier_document',
        status: 'pending',
        mode: 'create',
        supplier_id: 7,
        purchase_order_id: null,
        warnings: ['1 line item(s) need a Fulcrum product match before approval.'],
        created_at: '2026-05-11T00:00:00Z',
        reviewed_at: null,
        extracted_data: {
            mode: 'create',
            vendor_name: 'Alibaba Launch Supplier',
            po_number: 'ALI-1',
            invoice_number: null,
            document_date: null,
            currency: 'USD',
            subtotal: 42.75,
            shipping_cost: 0,
            tax_amount: 0,
            total_amount: 42.75,
            confidence: 0.8,
            matched_po_id: null,
            matched_po_number: null,
            matched_supplier_name: null,
            match_confidence: 0,
            matches: [],
            unmatched_po_items: [],
            unmatched_invoice_items: [],
            total_discrepancy: 0,
            items: [
                {
                    sku: 'ALI-NEW-001',
                    description: 'Alibaba New Customer Widget',
                    quantity: 3,
                    unit_cost: 14.25,
                    line_total: 42.75,
                    matched_product_id: null,
                    matched_variant_id: null
                }
            ]
        }
    };

    beforeEach(async () => {
        suppliersServiceMock = {
            getSuppliers: vi.fn().mockReturnValue(of([{ id: 7, name: 'Alibaba Launch Supplier' }])),
            createProductFromImportReviewItem: vi.fn(),
            learnAliasFromImportReviewItem: vi.fn()
        };
        productServiceMock = {
            getProducts: vi.fn().mockReturnValue(of({
                data: [{ id: 11, sku: 'FUL-11', name: 'Fulcrum Widget' }],
                currentPage: 1,
                totalPages: 1,
                totalItems: 1,
                pageSize: 500,
                hasNextPage: false,
                hasPrevPage: false
            }))
        };
        dialogRefMock = { close: vi.fn() };
        snackBarMock = { open: vi.fn() };

        await TestBed.configureTestingModule({
            imports: [
                PoIngestDialogComponent,
                MatDialogModule,
                NoopAnimationsModule,
                TranslocoTestingModule.forRoot({
                    langs: { en: {}, 'es-MX': {} },
                    translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' }
                })
            ],
            providers: [
                { provide: MAT_DIALOG_DATA, useValue: { review: baseReview } },
                { provide: MatDialogRef, useValue: dialogRefMock },
                { provide: SuppliersService, useValue: suppliersServiceMock },
                { provide: ProductService, useValue: productServiceMock },
                { provide: SettingsService, useValue: { storeSettings$: of({ ai_config: { enabled: false } }) } },
                { provide: MatSnackBar, useValue: snackBarMock }
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(PoIngestDialogComponent);
        component = fixture.componentInstance;
        (component as any).snackBar = snackBarMock;
        fixture.detectChanges();
    });

    it('should create a product from an unmatched import line and update the review match', () => {
        const assistedReview = {
            ...baseReview,
            warnings: [],
            extracted_data: {
                ...baseReview.extracted_data,
                items: [
                    {
                        ...baseReview.extracted_data.items[0],
                        matched_product_id: 99
                    }
                ]
            }
        };
        suppliersServiceMock.createProductFromImportReviewItem.mockReturnValue(of({
            import_review: assistedReview,
            product: { id: 99, sku: 'ALI-NEW-001', name: 'Alibaba New Customer Widget' },
            alias: { id: 5, alias_sku: 'ALI-NEW-001' }
        }));

        component.createProductForItem(component.editableItems[0], 0);

        expect(suppliersServiceMock.createProductFromImportReviewItem).toHaveBeenCalledWith(
            42,
            0,
            {
                supplier_id: 7,
                name: 'Alibaba New Customer Widget',
                sku: 'ALI-NEW-001',
                default_resale_price: 14.25,
                create_alias: true
            }
        );
        expect(component.editableItems[0].matched_product_id).toBe(99);
        expect(component.reviewWarnings).toEqual([]);
        expect(component.products.some(product => product.id === 99)).toBe(true);
        expect(snackBarMock.open).toHaveBeenCalledWith(
            'Product created and matched to this line',
            'Close',
            { duration: 3000 }
        );
    });

    it('should learn an alias for a selected product and update the review match', () => {
        component.editableItems[0].matched_product_id = 11;
        const assistedReview = {
            ...baseReview,
            warnings: [],
            extracted_data: {
                ...baseReview.extracted_data,
                items: [
                    {
                        ...baseReview.extracted_data.items[0],
                        matched_product_id: 11
                    }
                ]
            }
        };
        suppliersServiceMock.learnAliasFromImportReviewItem.mockReturnValue(of({
            import_review: assistedReview,
            product: { id: 11, sku: 'FUL-11', name: 'Fulcrum Widget' },
            alias: { id: 6, alias_sku: 'ALI-NEW-001', alias_name: 'Alibaba New Customer Widget' }
        }));

        component.learnAliasForItem(component.editableItems[0], 0);

        expect(suppliersServiceMock.learnAliasFromImportReviewItem).toHaveBeenCalledWith(
            42,
            0,
            {
                supplier_id: 7,
                product_id: 11,
                variant_id: null,
                alias_sku: 'ALI-NEW-001',
                alias_name: 'Alibaba New Customer Widget'
            }
        );
        expect(component.editableItems[0].matched_product_id).toBe(11);
        expect(component.reviewWarnings).toEqual([]);
        expect(snackBarMock.open).toHaveBeenCalledWith(
            'Supplier alias learned for this line',
            'Close',
            { duration: 3000 }
        );
    });
});
