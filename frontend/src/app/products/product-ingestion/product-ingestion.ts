import { Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { NgxScannerQrcodeComponent } from 'ngx-scanner-qrcode';
import { Subscription } from 'rxjs';
import { HardwareService } from '../../core/services/hardware.service';

@Component({
  selector: 'app-product-ingestion',
  templateUrl: './product-ingestion.html',
  styleUrls: ['./product-ingestion.scss'],
})
export class ProductIngestion implements OnInit, OnDestroy {
  @ViewChild('scanner') scanner!: NgxScannerQrcodeComponent;
  
  public cameraStream: MediaStream | null = null;
  public scannedData: any = null;
  public capturedImage: Blob | null = null;

  private streamSubscription?: Subscription;

  constructor(private hardwareService: HardwareService) {}

  ngOnInit(): void {
    this.streamSubscription = this.hardwareService.getCameraStream().subscribe({
      next: (stream) => {
        this.cameraStream = stream;
        this.scanner.start();
      },
      error: (err) => {
        console.error('Error accessing camera:', err);
        // Handle camera access error (e.g., show a message to the user)
      },
    });
  }

  ngOnDestroy(): void {
    if (this.streamSubscription) {
      this.streamSubscription.unsubscribe();
    }
    if (this.cameraStream) {
      this.cameraStream.getTracks().forEach(track => track.stop());
    }
  }

  onScanSuccess(result: any): void {
    this.scannedData = result;
    // Here you would typically call a service to fetch product data using the barcode
    console.log('Barcode scanned:', result);
  }

  capturePhoto(): void {
    if (this.cameraStream) {
      this.hardwareService.captureImage(this.cameraStream)
        .then(blob => {
          this.capturedImage = blob;
          // Here you would typically call a service to upload the image
          console.log('Image captured:', blob);
        })
        .catch(err => {
          console.error('Error capturing image:', err);
        });
    }
  }
}