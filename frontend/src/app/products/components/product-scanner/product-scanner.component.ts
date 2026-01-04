import { Component, ElementRef, EventEmitter, OnDestroy, Output, ViewChild, Optional, Inject, AfterViewInit, HostListener, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule } from '@ngneat/transloco';
import { AiService, ProductIdentificationResponse } from '../../../core/services/ai.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialogRef } from '@angular/material/dialog';
import { SettingsService } from '../../../core/services/settings.service';
import { MatTabsModule } from '@angular/material/tabs';
import { NgxScannerQrcodeComponent, ScannerQRCodeConfig, ScannerQRCodeResult } from 'ngx-scanner-qrcode';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { Router } from '@angular/router';
import { Product } from '../../models/product.model';
import { ProductService } from '../../services/product';

@Component({
    selector: 'app-product-scanner',
    standalone: true,
    imports: [
        CommonModule,
        MatButtonModule,
        MatIconModule,
        MatProgressSpinnerModule,
        TranslocoModule,
        MatTabsModule,
        NgxScannerQrcodeComponent,
        FormsModule,
        MatFormFieldModule,
        MatInputModule,
        MatDividerModule,
        MatTooltipModule
    ],
    templateUrl: './product-scanner.component.html',
    styleUrls: ['./product-scanner.component.scss']
})
export class ProductScannerComponent implements OnDestroy, AfterViewInit {
    @Output() scanComplete = new EventEmitter<ProductIdentificationResponse | any>();
    @Output() close = new EventEmitter<void>();

    @ViewChild('videoElement') videoElement!: ElementRef<HTMLVideoElement>;
    @ViewChild('canvasElement') canvasElement!: ElementRef<HTMLCanvasElement>;
    @ViewChild('action') scanner!: NgxScannerQrcodeComponent;

    // Camera/AI State
    stream: MediaStream | null = null;
    isCameraActive = false;
    productFound = false;
    foundProduct: any = null;
    currentImageFile: File | null = null;
    isProcessing = false;
    isInitializing = false; // New: Camera is starting up
    isAnalyzing = false;    // New: AI is analyzing image
    cameraError = false;
    isAiEnabled = false;
    manualBarcode = '';
    activeTabIndex: number = 0; // Default to the first tab (Barcode)

    // Barcode State
    config: ScannerQRCodeConfig = {
        constraints: {
            video: {
                facingMode: 'environment' // Search back camera
            }
        },
    };

    constructor(
        private dialogRef: MatDialogRef<ProductScannerComponent>,
        private productService: ProductService,
        private snackBar: MatSnackBar,
        private router: Router,
        private settingsService: SettingsService,
        private aiService: AiService,
        private http: HttpClient,
        private cdr: ChangeDetectorRef
    ) { }

    ngOnInit(): void {
        // Force refresh store settings to ensure latest AI config
        this.settingsService.loadStoreSettings();

        // Need to check Store settings for AI config
        this.settingsService.storeSettings$.subscribe(storeSettings => {
            console.log('[Scanner] Store settings received:', storeSettings);
            if (storeSettings?.ai_config) {
                this.isAiEnabled = storeSettings.ai_config.enabled;
                console.log('[Scanner] AI Enabled:', this.isAiEnabled);
            }
        });

        // Sticky Tab: Restore last used tab index
        const savedIndex = localStorage.getItem('productScanner_activeTabIndex');
        if (savedIndex !== null) {
            this.activeTabIndex = parseInt(savedIndex, 10);
            // Validation: Ensure index is valid (0 or 1)
            if (this.activeTabIndex < 0 || this.activeTabIndex > 1) {
                this.activeTabIndex = 0;
            }
        }
    }

    ngAfterViewInit(): void {
        // Auto-start the camera if we land on Tab 1 (Identify)
        setTimeout(() => {
            if (this.activeTabIndex === 0) {
                this.startCamera();
            } else if (this.activeTabIndex === 1) {
                // Focus input if starting on Barcode tab
                const input = document.querySelector('.barcode-input input') as HTMLElement;
                if (input) input.focus();
            }
        }, 500);
    }

    ngOnDestroy(): void {
        this.stopCamera();
        this.stopBarcodeScanner();
    }

    // --- Tabs Handling ---
    onTabChange(index: number) {
        this.activeTabIndex = index;
        localStorage.setItem('productScanner_activeTabIndex', index.toString());

        // Stop everything first
        this.stopCamera();
        this.stopBarcodeScanner();

        // Auto-start respective camera logic
        setTimeout(() => {
            if (index === 0) {
                // Tab 1: Identify -> Auto-start camera
                this.startCamera();
            }
            // Tab 2: Scan Barcode -> Do NOT auto-start camera (user must click "Use Camera")
            // Focus on input field for hardware scanner
            if (index === 1) {
                const input = document.querySelector('.barcode-input input') as HTMLElement;
                if (input) input.focus();
            }
        }, 300);
    }

    // --- AI Camera Logic ---

    async startCamera(): Promise<void> {
        this.cameraError = false;
        this.isInitializing = true;
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment' }
            });
            if (this.videoElement) {
                this.videoElement.nativeElement.srcObject = this.stream;
                this.isCameraActive = true;
            }
        } catch (err) {
            console.error('Error accessing camera', err);
            this.cameraError = true;
            this.snackBar.open('Could not access camera', 'Close', { duration: 3000 });
        } finally {
            this.isInitializing = false;
        }
    }

    stopCamera(): void {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
            this.isCameraActive = false;
        }
    }

    capturePhoto(): void {
        if (!this.stream || !this.videoElement || !this.canvasElement) return;

        const video = this.videoElement.nativeElement;
        const canvas = this.canvasElement.nativeElement;

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        const context = canvas.getContext('2d');
        if (context) {
            context.drawImage(video, 0, 0, canvas.width, canvas.height);

            canvas.toBlob(blob => {
                if (blob) {
                    this.processImage(new File([blob], 'capture.jpg', { type: 'image/jpeg' }));
                }
            }, 'image/jpeg', 0.9);
        }
    }

    onFileSelected(event: Event): void {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files[0]) {
            this.processImage(input.files[0]);
        }
    }

    processImage(file: File): void {
        console.log('[Scanner] processImage called. isAiEnabled:', this.isAiEnabled);
        this.isProcessing = true;
        this.stopCamera();

        if (!this.isAiEnabled) {
            // Manual Mode: Just emit the file
            console.log('[Scanner] AI disabled, using manual mode');
            const result = { imageFile: file };
            this.scanComplete.emit(result as any);
            if (this.dialogRef) this.dialogRef.close(result);
            this.isProcessing = false;
            return;
        }

        console.log('[Scanner] Calling AI service...');
        this.isAnalyzing = true; // Start analysis overlay

        // Save file for later use if we find a duplicate
        this.currentImageFile = file;

        this.aiService.identifyProduct(file).subscribe({
            next: (response) => {
                console.log('[Scanner] AI Response received:', response);
                this.isProcessing = false;
                this.isAnalyzing = false;

                // Check for existing product
                if (response.exists) {
                    console.log('[Scanner] Product exists in database');
                    this.productFound = true;
                    this.foundProduct = response;
                    this.cdr.detectChanges(); // Force update
                    // Don't close dialog yet - wait for user choice
                    return;
                }

                this.finishScan(response, file);
            },
            error: (err) => {
                console.error('AI Processing Error', err);
                this.snackBar.open('AI Identification failed. Using image for manual entry.', 'Close', { duration: 3000 });
                const result = { imageFile: file };
                this.scanComplete.emit(result as any);
                if (this.dialogRef) this.dialogRef.close(result);
                this.isProcessing = false;
                this.isAnalyzing = false;
            }
        });
    }

    finishScan(response: any, file: File): void {
        // Combine AI response with the original file
        const result = { ...response, imageFile: file };
        console.log('[Scanner] Closing dialog with result:', result);
        this.scanComplete.emit(result);
        if (this.dialogRef) {
            this.dialogRef.close(result);
        }
    }

    editExisting(): void {
        if (this.foundProduct && this.foundProduct.product_id) {
            this.dialogRef.close({
                action: 'edit-existing',
                productId: this.foundProduct.product_id,
                originalResponse: this.foundProduct
            });
        }
    }

    createNewCopy(): void {
        if (this.foundProduct && this.currentImageFile) {
            // Treat as new but pre-filled with the found data
            this.finishScan(this.foundProduct, this.currentImageFile);
        }
    }

    // --- Bluetooth / Keyboard Scanner Support ---

    private barcodeBuffer: string = '';
    private barcodeTimeout: any;

    @HostListener('window:keydown', ['$event'])
    handleKeyboardEvent(event: KeyboardEvent) {
        // If user is typing in an input, ignore (unless it's the invisible focus trap, but here we scan globally in dialog)
        const target = event.target as HTMLElement;
        if ((target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') && !target.classList.contains('focus-trap')) {
            return;
        }

        if (event.key === 'Enter') {
            if (this.barcodeBuffer.length > 3) { // Min length check
                this.lookupProduct(this.barcodeBuffer);
                this.barcodeBuffer = '';
            }
            return;
        }

        if (event.key.length === 1) { // Printable char
            this.barcodeBuffer += event.key;

            // Reset buffer if typing is too slow (human typing vs scanner)
            // Scanners are fast. 50-100ms per char.
            clearTimeout(this.barcodeTimeout);
            this.barcodeTimeout = setTimeout(() => {
                this.barcodeBuffer = '';
            }, 200); // 200ms gap resets buffer
        }
    }

    // --- Barcode Logic ---

    startBarcodeScanner() {
        // Small delay to ensure the scanner component is fully rendered
        setTimeout(() => {
            if (!this.scanner) {
                this.snackBar.open('Scanner not ready. Please try again.', 'Close', { duration: 3000 });
                return;
            }

            this.scanner.start().subscribe({
                next: (res) => {
                    console.log('Scanner started', res);
                    // UX Improvement: Disable PiP on the scanner video
                    setTimeout(() => {
                        const videos = document.querySelectorAll('ngx-scanner-qrcode video');
                        videos.forEach((v: any) => {
                            if (v) {
                                v.disablePictureInPicture = true;
                                v.setAttribute('disablePictureInPicture', 'true');
                                // Force style if needed
                                v.style.objectFit = 'cover';
                            }
                        });
                    }, 500);
                },
                error: (err) => {
                    console.error('Scanner start failed', err);
                    // Provide user-friendly error messages
                    let message = 'Scanner Error: ';
                    if (err?.message?.includes('NotAllowedError') || err?.name === 'NotAllowedError') {
                        message += 'Camera permission denied. Please allow camera access.';
                    } else if (err?.message?.includes('NotFoundError') || err?.name === 'NotFoundError') {
                        message += 'No camera found. Please connect a camera.';
                    } else if (err?.message?.includes('object can not be found')) {
                        message += 'Camera not available. Try refreshing the page.';
                    } else {
                        message += err?.message || 'Unknown error';
                    }
                    this.snackBar.open(message, 'Close', { duration: 5000 });
                }
            });
        }, 100);
    }

    stopBarcodeScanner() {
        if (this.scanner) {
            this.scanner.stop();
        }
    }

    onManualBarcodeSubmit(): void {
        if (this.manualBarcode?.trim()) {
            this.lookupProduct(this.manualBarcode.trim());
            this.manualBarcode = ''; // Clear after submit
        }
    }

    onBarcodeEvent(e: ScannerQRCodeResult[], action?: any): void {
        if (e && e.length > 0) {
            const result = e[0];
            if (result.value) {
                // Audio beep feedback could be good here
                this.stopBarcodeScanner();
                this.lookupProduct(result.value);
            }
        }
    }

    lookupProduct(barcode: string): void {
        this.isProcessing = true;
        this.http.get<Product>(`${environment.apiUrl}/products/lookup/barcode`, { params: { barcode } }).subscribe({
            next: (product: Product) => {
                this.isProcessing = false;
                // Product found! Close with product data
                const result = { foundProduct: product, barcode };
                this.scanComplete.emit(result);
                if (this.dialogRef) this.dialogRef.close(result);
                this.snackBar.open('Product found!', 'Close', { duration: 2000 });
            },
            error: (err) => {
                this.isProcessing = false;
                if (err.status === 404) {
                    // Not found -> Prompt to create
                    this.snackBar.open('Product not found. Opening creation form...', 'Close', { duration: 3000 });
                    const result = { barcode, notFound: true };
                    this.scanComplete.emit(result);
                    if (this.dialogRef) this.dialogRef.close(result);
                } else {
                    this.snackBar.open('Error looking up barcode.', 'Close', { duration: 3000 });
                }
            }
        });
    }

    closeDialog(): void {
        this.close.emit();
        if (this.dialogRef) {
            this.dialogRef.close();
        }
    }
}
