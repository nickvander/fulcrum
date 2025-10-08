import { Component, OnDestroy, AfterViewInit, ViewChild } from '@angular/core';
import { NgxScannerQrcodeComponent } from 'ngx-scanner-qrcode';
import { HardwareService } from '../../core/services/hardware.service';
import { SharedModule } from '../../shared/shared-module';

@Component({
  selector: 'app-product-ingestion',
  templateUrl: './product-ingestion.html',
  styleUrls: ['./product-ingestion.scss'],
  standalone: true,
  imports: [SharedModule, NgxScannerQrcodeComponent],
})
export class ProductIngestion implements AfterViewInit, OnDestroy {
  @ViewChild('scanner') scanner!: NgxScannerQrcodeComponent;

  public scannedData: any = null;
  public capturedImage: Blob | null = null;

  // Keep HardwareService for photo capture
  constructor(private hardwareService: HardwareService) {}

  ngAfterViewInit(): void {
    // The scanner component will automatically start
  }

  ngOnDestroy(): void {
    // Stop the scanner when the component is destroyed
    this.scanner.stop();
  }

  onScanSuccess(result: any): void {
    this.scannedData = result;
    // Here you would typically call a service to fetch product data using the barcode
    console.log('Barcode scanned:', result);
    this.scanner.stop(); // Stop scanning after a successful scan
  }

  capturePhoto(): void {
    // Use a separate stream for photo capture
    const streamSub = this.hardwareService.getCameraStream().subscribe({
      next: (stream) => {
        this.hardwareService
          .captureImage(stream)
          .then((blob) => {
            this.capturedImage = blob;
            // Here you would typically call a service to upload the image
            console.log('Image captured:', blob);
          })
          .catch((err) => {
            console.error('Error capturing image:', err);
          })
          .finally(() => {
            // Stop the tracks and unsubscribe
            stream.getTracks().forEach((track) => track.stop());
            streamSub.unsubscribe();
          });
      },
      error: (err) => {
        console.error('Error accessing camera for photo:', err);
      },
    });
  }
}