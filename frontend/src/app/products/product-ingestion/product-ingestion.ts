import { Component, OnDestroy, AfterViewInit, ViewChild } from '@angular/core';
import { Router } from '@angular/router';
import { NgxScannerQrcodeComponent } from 'ngx-scanner-qrcode';
import { HardwareService } from '../../core/services/hardware.service';
import { SharedModule } from '../../shared/shared-module';
import { ProductService } from '../services/product';
import { switchMap, from, tap } from 'rxjs';
import { TranslocoModule } from '@ngneat/transloco';

@Component({
  selector: 'app-product-ingestion',
  templateUrl: './product-ingestion.html',
  styleUrls: ['./product-ingestion.scss'],
  standalone: true,
  imports: [SharedModule, NgxScannerQrcodeComponent, TranslocoModule],
})
export class ProductIngestion implements AfterViewInit, OnDestroy {
  @ViewChild('scanner') scanner!: NgxScannerQrcodeComponent;

  public scannedData: any = null;
  public capturedImage: Blob | null = null;

  constructor(
    private hardwareService: HardwareService,
    private productService: ProductService,
    private router: Router
  ) { }

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
    this.scanner.stop(); // Stop scanning after a successful scan

    this.productService.searchProductsBySku(result).subscribe((paginatedResult: any) => {
      // Check if result is PaginatedProducts or just an array
      const products = Array.isArray(paginatedResult) ? paginatedResult : paginatedResult.data || [];

      if (products.length > 0) {
        // Product found, navigate to the edit page
        this.router.navigate(['/products', products[0].id, 'edit']);
      } else {
        // No product found, navigate to the create page with the SKU pre-filled
        this.router.navigate(['/products/new'], { state: { productData: { sku: result } } });
      }
    });
  }

  capturePhoto(): void {
    this.hardwareService.getCameraStream().pipe(
      switchMap(stream =>
        from(this.hardwareService.captureImage(stream)).pipe(
          tap(blob => this.capturedImage = blob),
          switchMap(blob => {
            const file = new File([blob], 'ingestion.jpg', { type: 'image/jpeg' });
            return this.productService.uploadImage(file);
          }),
          switchMap(uploadResult =>
            this.productService.identifyProductFromImage(uploadResult.file_path)
          ),
          tap(() => stream.getTracks().forEach(track => track.stop()))
        )
      )
    ).subscribe(productData => {
      this.router.navigate(['/products/new'], { state: productData });
    });
  }
}