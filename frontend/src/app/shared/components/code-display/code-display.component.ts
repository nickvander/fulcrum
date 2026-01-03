import { Component, Input, ElementRef, ViewChild, AfterViewInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import JsBarcode from 'jsbarcode';
import QRCode from 'qrcode';

@Component({
  selector: 'app-code-display',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule, MatTooltipModule],
  template: `
    <div class="code-container" *ngIf="value">
      <canvas #codeCanvas></canvas>
      <div class="code-text">{{ value }}</div>
      <div class="code-actions" *ngIf="showActions">
        <button mat-icon-button (click)="copyValue()" matTooltip="Copy">
          <mat-icon>content_copy</mat-icon>
        </button>
        <button mat-icon-button (click)="print()" matTooltip="Print Label">
          <mat-icon>print</mat-icon>
        </button>
      </div>
    </div>
  `,
  styles: [`
    .code-container {
      display: inline-flex;
      flex-direction: column;
      align-items: center;
      padding: 12px;
      background: white;
      border-radius: 8px;
    }
    canvas {
      max-width: 100%;
    }
    .code-text {
      font-family: monospace;
      font-size: 11px;
      color: #333;
      margin-top: 6px;
      text-align: center;
      word-break: break-all;
      max-width: 200px;
    }
    .code-actions {
      display: flex;
      gap: 4px;
      margin-top: 8px;
      button {
        width: 32px;
        height: 32px;
        mat-icon { font-size: 18px; width: 18px; height: 18px; }
      }
    }
  `]
})
export class CodeDisplayComponent implements AfterViewInit, OnChanges {
  @Input() value: string = '';
  @Input() type: 'barcode' | 'qrcode' = 'barcode';
  @Input() format: string = 'CODE128';
  @Input() showActions: boolean = true;

  @ViewChild('codeCanvas') canvasRef!: ElementRef<HTMLCanvasElement>;

  ngAfterViewInit(): void {
    this.generateCode();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if ((changes['value'] || changes['type']) && this.canvasRef) {
      setTimeout(() => this.generateCode(), 0);
    }
  }

  private generateCode(): void {
    if (!this.value || !this.canvasRef) return;
    const canvas = this.canvasRef.nativeElement;

    if (this.type === 'barcode') {
      this.generateBarcode(canvas);
    } else {
      this.generateQRCode(canvas);
    }
  }

  private generateBarcode(canvas: HTMLCanvasElement): void {
    try {
      JsBarcode(canvas, this.value, {
        format: this.format,
        width: 2,
        height: 60,
        displayValue: false,
        margin: 10
      });
    } catch (e) {
      // Fallback to CODE128 which accepts any string
      try {
        JsBarcode(canvas, this.value, {
          format: 'CODE128',
          width: 2,
          height: 60,
          displayValue: false,
          margin: 10
        });
      } catch (e2) {
        console.error('Barcode generation failed:', e2);
      }
    }
  }

  private generateQRCode(canvas: HTMLCanvasElement): void {
    QRCode.toCanvas(canvas, this.value, {
      width: 150,
      margin: 2,
      errorCorrectionLevel: 'M'
    }, (error: any) => {
      if (error) console.error('QR code generation failed:', error);
    });
  }

  copyValue(): void {
    navigator.clipboard.writeText(this.value);
  }

  print(): void {
    const canvas = this.canvasRef.nativeElement;
    const dataUrl = canvas.toDataURL('image/png');

    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(`
        <html>
          <head><title>Print Label</title>
            <style>
              body { display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; flex-direction: column; }
              img { max-width: 100%; }
              .value { font-family: monospace; margin-top: 12px; font-size: 14px; }
            </style>
          </head>
          <body>
            <img src="${dataUrl}" />
            <div class="value">${this.value}</div>
          </body>
        </html>
      `);
      printWindow.document.close();
      setTimeout(() => { printWindow.print(); printWindow.close(); }, 250);
    }
  }
}
