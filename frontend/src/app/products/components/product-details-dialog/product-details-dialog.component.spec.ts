
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ProductDetailsDialogComponent } from './product-details-dialog.component';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialog } from '@angular/material/dialog';
import { ProductService } from '../../services/product';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Product } from '../../models/product.model';
import { TranslocoTestingModule } from '@ngneat/transloco';

describe('ProductDetailsDialogComponent', () => {
    let component: ProductDetailsDialogComponent;
    let fixture: ComponentFixture<ProductDetailsDialogComponent>;
    let dialogRefMock: any;
    let productServiceMock: any;
    let routerMock: any;
    let dialogMock: any;

    const mockProduct: Product = {
        id: 1,
        name: 'Test Product',
        sku: 'TEST-SKU',
        description: 'Test Description',
        default_resale_price: 100,
        cost_price: 50,
        images: [],
        custom_fields: [],
        is_bundle: false
    };

    beforeEach(async () => {
        dialogRefMock = {
            close: vi.fn()
        };

        productServiceMock = {
            getProductById: vi.fn().mockReturnValue(of(mockProduct)),
            getPurchaseHistory: vi.fn().mockReturnValue(of([])),
            assembleBundle: vi.fn().mockReturnValue(of({ ...mockProduct }))
        };

        routerMock = {
            navigate: vi.fn()
        };

        dialogMock = {
            open: vi.fn()
        };

        await TestBed.configureTestingModule({
            imports: [
                ProductDetailsDialogComponent,
                NoopAnimationsModule,
                TranslocoTestingModule.forRoot({
                    langs: { en: {}, 'es-MX': {} },
                    translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' }
                })
            ],
            providers: [
                { provide: MatDialogRef, useValue: dialogRefMock },
                {
                    provide: MAT_DIALOG_DATA,
                    useValue: { product: mockProduct, mode: 'view' }
                },
                { provide: ProductService, useValue: productServiceMock },
                { provide: Router, useValue: routerMock },
                { provide: MatDialog, useValue: dialogMock }
            ]
        }).compileComponents();

        // Override MatDialog provider to ensure mock is used (similar to campaign-detail fix)
        TestBed.overrideProvider(MatDialog, { useValue: dialogMock });

        fixture = TestBed.createComponent(ProductDetailsDialogComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should initialize with product data', () => {
        expect(component.product).toEqual(mockProduct);
    });

    it('should load history on init', () => {
        expect(productServiceMock.getPurchaseHistory).toHaveBeenCalledWith(mockProduct.id);
    });

    it('should switch to edit mode', () => {
        component.onEdit();
        expect(component.isEditMode).toBe(true);
    });

    it('should navigate to PO and close dialog', async () => {
        await component.onGoToPO(123);
        expect(routerMock.navigate).toHaveBeenCalledWith(['/suppliers/po', 123]);
        expect(dialogRefMock.close).toHaveBeenCalled();
    });
});
