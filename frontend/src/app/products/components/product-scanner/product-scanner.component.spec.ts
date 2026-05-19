import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ProductScannerComponent } from './product-scanner.component';
import { AiService } from '../../../core/services/ai.service';
import { SettingsService } from '../../../core/services/settings.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of } from 'rxjs';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { MatDialogRef } from '@angular/material/dialog';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Component, Input, Output, EventEmitter } from '@angular/core';


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
            identifyProduct: vi.fn(),
            isReady$: vi.fn().mockReturnValue(of(true)),
            getCapabilities: vi.fn().mockReturnValue(of({ ready: true, enabled: true, configured: true, provider: 'google' })),
            invalidateCapabilities: vi.fn()
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
        })
            .compileComponents();

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

        component.lookupProduct(mockBarcode);

        const req = httpTestingController.expectOne(req => req.url.includes('/products/lookup/barcode'));
        req.flush('Not Found', { status: 404, statusText: 'Not Found' });

        expect(snackBarSpy.open).toHaveBeenCalledWith('Product not found. Opening creation form...', 'Close', expect.anything());
        expect(component.scanComplete.emit).toHaveBeenCalledWith({ barcode: mockBarcode, notFound: true });
        expect(dialogRefSpy.close).toHaveBeenCalled();
    });

    it('should handle drag events', () => {
        const dragEvent = {
            preventDefault: vi.fn(),
            stopPropagation: vi.fn(),
            type: 'dragover'
        } as unknown as DragEvent;

        component.onDragOver(dragEvent);
        expect(component.isDragOver).toBe(true);
        expect(dragEvent.preventDefault).toHaveBeenCalled();

        component.onDragLeave(dragEvent);
        expect(component.isDragOver).toBe(false);
    });

    it('should handle file drop with image', () => {
        const mockFile = new File([''], 'test.png', { type: 'image/png' });
        const dropEvent = {
            preventDefault: vi.fn(),
            stopPropagation: vi.fn(),
            dataTransfer: {
                files: [mockFile]
            }
        } as unknown as DragEvent;

        vi.spyOn(component, 'processImage').mockImplementation(() => { });

        component.onDrop(dropEvent);

        expect(component.isDragOver).toBe(false);
        expect(component.processImage).toHaveBeenCalledWith(mockFile);
        expect(dropEvent.preventDefault).toHaveBeenCalled();
    });

    it('should reject non-image file drop', () => {
        const mockFile = new File([''], 'test.txt', { type: 'text/plain' });
        const dropEvent = {
            preventDefault: vi.fn(),
            stopPropagation: vi.fn(),
            dataTransfer: {
                files: [mockFile]
            }
        } as unknown as DragEvent;

        vi.spyOn(component, 'processImage').mockImplementation(() => { });

        component.onDrop(dropEvent);

        expect(component.processImage).not.toHaveBeenCalled();
        expect(snackBarSpy.open).toHaveBeenCalledWith('Please drop an image file.', 'Close', expect.anything());
    });
});
