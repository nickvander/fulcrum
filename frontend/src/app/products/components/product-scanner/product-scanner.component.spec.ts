import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ProductScannerComponent } from './product-scanner.component';
import { AiService } from '../../../core/services/ai.service';
import { SettingsService } from '../../../core/services/settings.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { MatDialogRef } from '@angular/material/dialog';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { NgxScannerQrcodeComponent } from 'ngx-scanner-qrcode';

describe('ProductScannerComponent', () => {
    let component: ProductScannerComponent;
    let fixture: ComponentFixture<ProductScannerComponent>;
    let aiServiceSpy: any;
    let snackBarSpy: any;
    let dialogRefSpy: any;
    let settingsServiceSpy: any;
    let httpTestingController: HttpTestingController;

    beforeEach(async () => {
        aiServiceSpy = {
            identifyProduct: vi.fn()
        };
        snackBarSpy = {
            open: vi.fn()
        };
        dialogRefSpy = {
            close: vi.fn()
        };
        settingsServiceSpy = {
            storeSettings$: of({ ai_config: { google_configured: true, enabled: true } }),
            loadStoreSettings: vi.fn()
        };

        await TestBed.configureTestingModule({
            imports: [
                ProductScannerComponent,
                TranslocoTestingModule.forRoot({ langs: { en: {} }, translocoConfig: { availableLangs: ['en'], defaultLang: 'en' } }),
                NoopAnimationsModule
            ],
            providers: [
                provideHttpClient(),
                provideHttpClientTesting(),
                { provide: AiService, useValue: aiServiceSpy },
                { provide: MatSnackBar, useValue: snackBarSpy },
                { provide: MatDialogRef, useValue: dialogRefSpy },
                { provide: SettingsService, useValue: settingsServiceSpy }
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(ProductScannerComponent);
        component = fixture.componentInstance;
        httpTestingController = TestBed.inject(HttpTestingController);
        fixture.detectChanges();
    });

    afterEach(() => {
        httpTestingController.verify();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should process image via AI when enabled', () => {
        const mockFile = new File([''], 'test.jpg', { type: 'image/jpeg' });
        const mockResponse = { name: 'Test Product', description: 'Desc', exists: false };
        aiServiceSpy.identifyProduct.mockReturnValue(of(mockResponse));

        vi.spyOn(component.scanComplete, 'emit');

        component.processImage(mockFile);

        expect(aiServiceSpy.identifyProduct).toHaveBeenCalledWith(mockFile);
        expect(component.isProcessing).toBe(false);
        expect(component.scanComplete.emit).toHaveBeenCalledWith(expect.objectContaining({ ...mockResponse, imageFile: mockFile }));
        expect(dialogRefSpy.close).toHaveBeenCalled();
    });

    it('should handle existing product detection', () => {
        const mockFile = new File([''], 'test.jpg', { type: 'image/jpeg' });
        const mockResponse = {
            name: 'Existing Product',
            sku: 'EXIST-123',
            exists: true,
            product_id: 123
        };
        aiServiceSpy.identifyProduct.mockReturnValue(of(mockResponse));

        vi.spyOn(component.scanComplete, 'emit');

        component.processImage(mockFile);

        expect(aiServiceSpy.identifyProduct).toHaveBeenCalledWith(mockFile);
        expect(component.productFound).toBe(true);
        expect(component.foundProduct).toEqual(mockResponse);
        // Should NOT close dialog or emit scanComplete yet
        expect(component.scanComplete.emit).not.toHaveBeenCalled();
        expect(dialogRefSpy.close).not.toHaveBeenCalled();
    });

    it('should perform barcode lookup', () => {
        const mockBarcode = '123456789';
        const mockProduct = { id: 1, name: 'Barcode Product', sku: 'TEST-SKU' };
        vi.spyOn(component.scanComplete, 'emit');

        // Mock scanner component reference since it's ViewChild
        component.scanner = { stop: vi.fn() } as any;

        component.lookupProduct(mockBarcode);

        const req = httpTestingController.expectOne(req => req.url.includes('/products/lookup/barcode') && req.params.get('barcode') === mockBarcode);
        expect(req.request.method).toBe('GET');
        req.flush(mockProduct);

        expect(component.scanComplete.emit).toHaveBeenCalledWith({ foundProduct: mockProduct, barcode: mockBarcode });
        expect(dialogRefSpy.close).toHaveBeenCalled();
        expect(snackBarSpy.open).toHaveBeenCalledWith('Product found!', 'Close', expect.anything());
    });

    it('should handle barcode not found', () => {
        const mockBarcode = '999999';
        vi.spyOn(component.scanComplete, 'emit');
        component.scanner = { stop: vi.fn() } as any;

        component.lookupProduct(mockBarcode);

        const req = httpTestingController.expectOne(req => req.url.includes('/products/lookup/barcode'));
        req.flush('Not Found', { status: 404, statusText: 'Not Found' });

        expect(snackBarSpy.open).toHaveBeenCalledWith('Product not found. Opening creation form...', 'Close', expect.anything());
        expect(component.scanComplete.emit).toHaveBeenCalledWith({ barcode: mockBarcode, notFound: true });
        expect(dialogRefSpy.close).toHaveBeenCalled();
    });
});
