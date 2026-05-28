import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  ElementRef,
  OnDestroy,
  ViewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { BarcodeDetector as BarcodeDetectorPolyfill } from 'barcode-detector/pure';
import { TranslocoModule } from '@ngneat/transloco';


/**
 * Lightweight scan dialog scoped to the count-session detail page.
 *
 * Two ways to enter a SKU:
 *   1. Camera barcode scan (preferred on phones — operators with
 *      laser-scanner sleds also benefit because most sleds emulate a
 *      keyboard and dump into the first focused input).
 *   2. Manual type-and-submit fallback for when the camera permission
 *      is denied or the SKU label is too damaged to read.
 *
 * Returns the detected/typed value as a plain string via dialog close;
 * the parent treats it as a SKU and calls its existing `addItem`
 * service.
 *
 * Why not reuse `ProductScannerComponent`: that dialog tries to do
 * full product identification (AI image lookup, product autofill),
 * which is overkill here — the count workflow just needs the SKU
 * string to feed into the existing add-by-sku endpoint.
 */
@Component({
  selector: 'app-scan-sku-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    TranslocoModule,
  ],
  templateUrl: './scan-sku-dialog.component.html',
  styleUrls: ['./scan-sku-dialog.component.scss'],
})
export class ScanSkuDialogComponent implements AfterViewInit, OnDestroy {
  @ViewChild('videoElement') videoElement!: ElementRef<HTMLVideoElement>;

  /** Manual entry input — fallback when the camera is unavailable. */
  manualValue = '';

  /** Whether the camera stream is up and the scan loop is running. */
  scanning = false;
  /** Camera permission denied / no device / unsupported browser. */
  cameraError: string | null = null;

  private stream: MediaStream | null = null;
  private detector: any = null;
  private rafId: number | null = null;

  constructor(
    private dialogRef: MatDialogRef<ScanSkuDialogComponent, string>,
    private cdr: ChangeDetectorRef,
  ) {}

  async ngAfterViewInit(): Promise<void> {
    // Don't crash if the platform doesn't support BarcodeDetector or
    // camera access — render the manual-entry side and let the
    // operator type in the SKU. We log nothing because the message in
    // the template already explains what happened.
    if (!('mediaDevices' in navigator)) {
      this.cameraError = 'no-media';
      this.cdr.markForCheck();
      return;
    }
    try {
      // Prefer the native BarcodeDetector when available; fall back to
      // the polyfill which works in Firefox + iOS Safari (uses ZXing
      // under the hood).
      const NativeBD = (window as any).BarcodeDetector;
      this.detector = NativeBD
        ? new NativeBD({ formats: ['code_128', 'ean_13', 'ean_8', 'qr_code', 'code_39'] })
        : new BarcodeDetectorPolyfill({
          formats: ['code_128', 'ean_13', 'ean_8', 'qr_code', 'code_39'],
        });
      await this.startCamera();
    } catch (e: any) {
      this.cameraError = e?.name === 'NotAllowedError' ? 'denied' : 'unavailable';
      this.cdr.markForCheck();
    }
  }

  ngOnDestroy(): void {
    this.stopCamera();
  }

  /** Submit the manually-typed value. Enter / submit-button both
   *  route here. */
  submitManual(): void {
    const v = this.manualValue.trim();
    if (!v) return;
    this.dialogRef.close(v);
  }

  cancel(): void {
    this.dialogRef.close(undefined);
  }

  private async startCamera(): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({
      // `facingMode: 'environment'` asks for the back camera on
      // phones; on laptops it's ignored and the only camera is used.
      video: { facingMode: 'environment' },
      audio: false,
    });
    const video = this.videoElement.nativeElement;
    video.srcObject = this.stream;
    await video.play();
    this.scanning = true;
    this.cdr.markForCheck();
    this.scanLoop();
  }

  private stopCamera(): void {
    if (this.rafId != null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
    }
    this.scanning = false;
  }

  /** Scan loop — polls the camera frame at the browser's animation
   *  cadence. First successful detection closes the dialog. */
  private async scanLoop(): Promise<void> {
    if (!this.detector || !this.scanning) return;
    try {
      const video = this.videoElement.nativeElement;
      const barcodes = await this.detector.detect(video);
      if (barcodes && barcodes.length > 0) {
        const value = (barcodes[0].rawValue || '').trim();
        if (value) {
          this.dialogRef.close(value);
          return;
        }
      }
    } catch {
      // detector errors fall through to the next frame
    }
    this.rafId = requestAnimationFrame(() => this.scanLoop());
  }
}
