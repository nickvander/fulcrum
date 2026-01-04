import { Component, ElementRef, EventEmitter, OnDestroy, Output, ViewChild, Optional, Inject, AfterViewInit, HostListener, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BarcodeDetector as BarcodeDetectorPolyfill } from 'barcode-detector/pure';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { AiService, ProductIdentificationResponse } from '../../../core/services/ai.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialogRef } from '@angular/material/dialog';
import { SettingsService } from '../../../core/services/settings.service';
import { MatTabsModule } from '@angular/material/tabs';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { Router } from '@angular/router';
import { Product } from '../../models/product.model';
import { ProductService } from '../../services/product';

import { SafeUrlPipe } from '../../../shared/pipes/safe-url-pipe';

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
        FormsModule,
        MatFormFieldModule,
        MatInputModule,
        MatDividerModule,
        MatTooltipModule,
        SafeUrlPipe
    ],
    templateUrl: './product-scanner.component.html',
    styleUrls: ['./product-scanner.component.scss']
})
export class ProductScannerComponent implements OnDestroy, AfterViewInit {
    @Output() scanComplete = new EventEmitter<ProductIdentificationResponse | any>();
    @Output() close = new EventEmitter<void>();

    @ViewChild('videoElement') videoElement!: ElementRef<HTMLVideoElement>;
    @ViewChild('canvasElement') canvasElement!: ElementRef<HTMLCanvasElement>;
    @ViewChild('barcodeVideo') barcodeVideoElement!: ElementRef<HTMLVideoElement>;

    // Camera/AI State
    stream: MediaStream | null = null;
    isCameraActive = false;
    productFound = false;
    foundProduct: any = null;
    currentImageFile: File | null = null;
    isProcessing = false;
    isInitializing = false; // New: Camera is starting up
    isAnalyzing = false;    // New: AI is analyzing image
    analysisStatus: string = ''; // New: Agent thought process
    private analysisInterval: any;
    cameraError = false;
    isAiEnabled = false;
    manualBarcode = '';
    activeTabIndex: number = 0; // Default to the first tab (Barcode)
    showBarcodeScanner = false; // Controls conditional rendering of scanner

    // Native Barcode Scanner State
    private barcodeStream: MediaStream | null = null;
    private barcodeDetector: any = null; // BarcodeDetector API
    private scanAnimationFrame: number | null = null;

    constructor(
        private dialogRef: MatDialogRef<ProductScannerComponent>,
        private productService: ProductService,
        private snackBar: MatSnackBar,
        private router: Router,
        private settingsService: SettingsService,
        private aiService: AiService,
        private http: HttpClient,
        private translocoService: TranslocoService,
        private cdr: ChangeDetectorRef
    ) { }

    ngOnInit(): void {
        // Force refresh store settings to ensure latest AI config
        this.settingsService.loadStoreSettings();

        // Need to check Store settings for AI config
        this.settingsService.storeSettings$.subscribe(storeSettings => {

            if (storeSettings?.ai_config) {
                this.isAiEnabled = storeSettings.ai_config.enabled;

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
            // Tab 2: Scan Barcode -> Focus on barcode input, let user click button to start camera
            if (index === 1) {
                const input = document.querySelector('.hardware-scanner-section input') as HTMLElement;
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

        // Calculate aspect ratio to match the overlay (roughly 0.7 or 0.85 depending on screen)
        // Overlay is 85% width, 70% height
        const overlayWidth = 0.85;
        const overlayHeight = 0.7;

        // Source dimensions
        const vw = video.videoWidth;
        const vh = video.videoHeight;

        // Destination dimensions (crop area)
        const dw = vw * overlayWidth;
        const dh = vh * overlayHeight;

        // Start coordinates (center crop)
        const sx = (vw - dw) / 2;
        const sy = (vh - dh) / 2;

        canvas.width = dw;
        canvas.height = dh;

        const context = canvas.getContext('2d');
        if (context) {
            // Draw only the cropped area
            context.drawImage(video, sx, sy, dw, dh, 0, 0, dw, dh);

            canvas.toBlob(blob => {
                if (blob) {
                    this.processImage(new File([blob], 'capture.jpg', { type: 'image/jpeg' }));
                }
            }, 'image/jpeg', 0.9);
        }
    }

    isDragOver = false;

    onDragOver(event: DragEvent): void {
        event.preventDefault();
        event.stopPropagation();
        this.isDragOver = true;
    }

    onDragLeave(event: DragEvent): void {
        event.preventDefault();
        event.stopPropagation();
        this.isDragOver = false;
    }

    onDrop(event: DragEvent): void {
        event.preventDefault();
        event.stopPropagation();
        this.isDragOver = false;

        const files = event.dataTransfer?.files;
        if (files && files.length > 0) {
            const file = files[0];
            if (file.type.match(/image\/*/)) {
                this.processImage(file);
            } else {
                this.snackBar.open('Please drop an image file.', 'Close', { duration: 3000 });
            }
        }
    }

    onFileSelected(event: Event): void {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files[0]) {
            this.processImage(input.files[0]);
        }
    }

    processImage(file: File): void {

        this.isProcessing = true;
        this.stopCamera();

        if (!this.isAiEnabled) {
            // Manual Mode: Just emit the file

            const result = { imageFile: file };
            this.scanComplete.emit(result as any);
            if (this.dialogRef) this.dialogRef.close(result);
            this.isProcessing = false;
            return;
        }


        this.isAnalyzing = true; // Start analysis overlay
        this.startAnalysisSimulation();

        // Save file for later use if we find a duplicate
        this.currentImageFile = file;

        this.aiService.identifyProduct(file).subscribe({
            next: (response) => {
                this.stopAnalysisSimulation();
                this.isProcessing = false;
                this.isAnalyzing = false;

                // Check for existing product
                if (response.exists) {

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
                this.stopAnalysisSimulation();
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
            // Treat as new: Strip ALL unique identifiers to force fresh generation
            const cleanProduct = {
                ...this.foundProduct,
                id: null,
                product_id: null,
                sku: null,
                barcode_value: null,
                qrcode_value: null,
                exists: false, // Critical: Mark as non-existing so form generates new IDs
                // Keep useful data - Prioritize text from AI analysis if available!
                name: this.foundProduct.ai_name || this.foundProduct.name,
                description: this.foundProduct.ai_description || this.foundProduct.description,
                brand: this.foundProduct.ai_brand || this.foundProduct.brand,
            };
            console.log('[Scanner] Creating new copy with cleaned data:', cleanProduct);
            this.finishScan(cleanProduct, this.currentImageFile);
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

    // --- Barcode Logic (Native Implementation) ---

    async startNativeBarcodeScanner(): Promise<void> {
        console.log('Starting native barcode scanner...');

        // IMPORTANT: Stop Tab 1's camera first to avoid conflicts
        this.stopCamera();

        // IMPORTANT: Stop Tab 1's camera first to avoid conflicts
        this.stopCamera();

        try {
            // Initialize BarcodeDetector (Native or Polyfill)
            if ('BarcodeDetector' in window) {
                console.log('Using native BarcodeDetector API');
                this.barcodeDetector = new (window as any).BarcodeDetector({
                    formats: ['qr_code', 'ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_39', 'code_128', 'itf', 'codabar']
                });
            } else {
                console.log('Using BarcodeDetector Polyfill');
                this.barcodeDetector = new BarcodeDetectorPolyfill({
                    formats: ['qr_code', 'ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_39', 'code_128', 'itf', 'codabar']
                });
            }

            // Get camera stream
            this.barcodeStream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment' }
            });

            // Show the scanner UI
            this.showBarcodeScanner = true;
            this.cdr.detectChanges();

            // Wait for video element to be available, then attach stream
            setTimeout(() => {
                if (this.barcodeVideoElement?.nativeElement) {
                    const video = this.barcodeVideoElement.nativeElement;
                    video.srcObject = this.barcodeStream;
                    video.play();

                    // Start scanning loop
                    this.startBarcodeDetectionLoop(video);
                    console.log('Native barcode scanner started successfully');
                } else {
                    console.error('Video element not available');
                    this.stopNativeBarcodeScanner();
                }
            }, 100);

        } catch (err: any) {
            console.error('Failed to start native barcode scanner:', err);
            this.handleScannerError(err);
            this.showBarcodeScanner = false;
        }
    }

    private startBarcodeDetectionLoop(video: HTMLVideoElement): void {
        const scan = async () => {
            if (!this.showBarcodeScanner || !this.barcodeDetector) return;

            try {
                const barcodes = await this.barcodeDetector.detect(video);
                if (barcodes.length > 0) {
                    const barcode = barcodes[0];
                    console.log('Barcode detected:', barcode.rawValue);

                    // Process the barcode
                    this.processDetectedBarcode(barcode.rawValue);
                    return; // Stop scanning after successful detection
                }
            } catch (err) {
                // Detection can fail on some frames, that's ok
            }

            // Continue scanning
            this.scanAnimationFrame = requestAnimationFrame(scan);
        };

        this.scanAnimationFrame = requestAnimationFrame(scan);
    }

    private processDetectedBarcode(value: string): void {
        // Stop the scanner
        this.stopNativeBarcodeScanner();

        // Look up the product
        this.lookupProduct(value);
    }

    stopNativeBarcodeScanner(): void {
        console.log('Stopping native barcode scanner...');

        // Stop animation frame
        if (this.scanAnimationFrame) {
            cancelAnimationFrame(this.scanAnimationFrame);
            this.scanAnimationFrame = null;
        }

        // Stop stream
        if (this.barcodeStream) {
            this.barcodeStream.getTracks().forEach(track => track.stop());
            this.barcodeStream = null;
        }

        // Clear video source
        if (this.barcodeVideoElement?.nativeElement) {
            this.barcodeVideoElement.nativeElement.srcObject = null;
        }

        this.barcodeDetector = null;
        this.showBarcodeScanner = false;
    }

    private handleScannerError(err: any) {
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

    // Keep old method for backwards compatibility (now just calls native)
    startBarcodeScanner(event?: Event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        this.startNativeBarcodeScanner();
    }

    stopBarcodeScanner() {
        // Stop native scanner
        this.stopNativeBarcodeScanner();
    }
    onManualBarcodeSubmit(): void {
        if (this.manualBarcode?.trim()) {
            this.lookupProduct(this.manualBarcode.trim());
            this.manualBarcode = ''; // Clear after submit
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
                    this.snackBar.open(
                        this.translocoService.translate('products.scanner.errorLookingUpBarcode'),
                        this.translocoService.translate('common.close'),
                        { duration: 3000 }
                    );
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

    private startAnalysisSimulation() {
        const messages = [
            this.translocoService.translate('products.ai.status.analyzing'),
            this.translocoService.translate('products.ai.status.extracting'),
            this.translocoService.translate('products.ai.status.searching'),
            this.translocoService.translate('products.ai.status.comparing'),
            this.translocoService.translate('products.ai.status.synthesizing'),
            this.translocoService.translate('products.ai.status.finalizing')
        ];
        let index = 0;
        this.analysisStatus = messages[0];

        // Update message every 1.5 seconds
        if (this.analysisInterval) clearInterval(this.analysisInterval);
        this.analysisInterval = setInterval(() => {
            index = (index + 1) % messages.length;
            this.analysisStatus = messages[index];
            this.cdr.detectChanges();
        }, 1500);
    }

    private stopAnalysisSimulation() {
        if (this.analysisInterval) {
            clearInterval(this.analysisInterval);
            this.analysisInterval = null;
        }
    }
}
