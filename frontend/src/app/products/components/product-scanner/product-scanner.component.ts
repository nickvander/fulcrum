import { Component, ElementRef, EventEmitter, OnDestroy, Output, ViewChild, Optional, Inject, AfterViewInit, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDividerModule } from '@angular/material/divider';
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
        MatDividerModule
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
    isProcessing = false;
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
        private http: HttpClient
    ) { }

    ngOnInit(): void {
        // Need to check Store settings for AI config
        this.settingsService.storeSettings$.subscribe(storeSettings => {
            if (storeSettings?.ai_config) {
                this.isAiEnabled = storeSettings.ai_config.enabled;
                if (!this.isAiEnabled) {
                    this.activeTabIndex = 0; // If AI tab hidden, Barcode tab is first (index 0)
                }
            }
        });

        // Initial setup
        this.startBarcodeScanner();
    }

    ngAfterViewInit(): void {
        // Start camera automatically if in AI mode? Maybe wait for user.
    }

    ngOnDestroy(): void {
        this.stopCamera();
        this.stopBarcodeScanner();
    }

    // --- Tabs Handling ---
    onTabChange(index: number) {
        // Stop everything when switching tabs
        this.stopCamera();
        this.stopBarcodeScanner();
    }

    // --- AI Camera Logic ---

    async startCamera(): Promise<void> {
        this.cameraError = false;
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

        this.aiService.identifyProduct(file).subscribe({
            next: (response) => {
                this.isProcessing = false;
                // Combine AI response with the original file
                const result = { ...response, imageFile: file };
                this.scanComplete.emit(result);
                if (this.dialogRef) {
                    this.dialogRef.close(result);
                }
            },
            error: (err) => {
                console.error('AI Processing Error', err);
                this.snackBar.open('AI Identification failed. Using image for manual entry.', 'Close', { duration: 3000 });
                const result = { imageFile: file };
                this.scanComplete.emit(result as any);
                if (this.dialogRef) this.dialogRef.close(result);
                this.isProcessing = false;
            }
        });
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
                next: (res) => console.log('Scanner started', res),
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
