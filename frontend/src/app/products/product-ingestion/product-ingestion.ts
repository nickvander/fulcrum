import { Component, OnDestroy, AfterViewInit, ViewChild } from '@angular/core';
import { Router } from '@angular/router';
import { NgxScannerQrcodeComponent } from 'ngx-scanner-qrcode';
import { HardwareService } from '../../core/services/hardware.service';
import { SharedModule } from '../../shared/shared-module';
import { ProductService } from '../services/product';
import { switchMap } from 'rxjs';

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

  constructor(
    private hardwareService: HardwareService,
    private productService: ProductService,
    private router: Router
  ) {}

  ngAfterViewInit(): void {
    // The scanner component will automatically start
  }

  ngOnDestroy(): void {
    // Stop the scanner when the component is destroyed
    if (this.scanner) {
      this.scanner.stop();
    }
  }

  onScanSuccess(result: any): void {
    this.scannedData = result;
    // Here you would typically call a service to fetch product data using the barcode
    console.log('Barcode scanned:', result);
    this.scanner.stop(); // Stop scanning after a successful scan
  }

  capturePhoto(): void {
    const streamSub = this.hardwareService.getCameraStream().subscribe({
      next: (stream) => {
        this.hardwareService
          .captureImage(stream)
          .then((blob) => {
            this.capturedImage = blob;
            const file = new File([blob], 'ingestion.jpg', { type: 'image/jpeg' });
            this.productService.uploadImage(file).pipe(
              switchMap(uploadResult => 
                this.productService.identifyProductFromImage(uploadResult.file_path)
              )
            ).subscribe(productData => {
              this.router.navigate(['/products/new'], { state: { productData } });
            });
          })
          .catch((err) => {
            console.error('Error capturing image:', err);
          })
          .finally(() => {
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