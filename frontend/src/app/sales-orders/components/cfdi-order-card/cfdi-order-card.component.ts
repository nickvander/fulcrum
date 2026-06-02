import { Component, Input, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslocoModule } from '@ngneat/transloco';
import { finalize } from 'rxjs';

import { CfdiDocument, CfdiService } from '../../../core/services/cfdi.service';

/**
 * CFDI (factura) panel on the order detail page (FP-06).
 *
 * Shows the order's stamped/linked CFDI, or offers the right action:
 *  - **Stamp** — Fulcrum issues the CFDI via the PAC (self-invoiced channels).
 *  - **Link external UUID** — record a CFDI issued elsewhere (e.g. ML's
 *    automatic facturación), shown automatically when stamping returns a
 *    409 `marketplace_handled`.
 */
@Component({
  selector: 'app-cfdi-order-card',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    TranslocoModule,
  ],
  templateUrl: './cfdi-order-card.component.html',
  styleUrls: ['./cfdi-order-card.component.scss'],
})
export class CfdiOrderCardComponent implements OnChanges {
  @Input() orderId!: number;

  doc: CfdiDocument | null = null;
  loading = false;
  working = false;
  /** Surface the link-UUID form (manual or after a 409 marketplace_handled). */
  showLink = false;
  /** Hint shown when the channel issues its own CFDI. */
  marketplaceHandled = false;
  /** Issuer not configured yet → point the operator at Settings. */
  issuerMissing = false;
  errorKey: string | null = null;

  linkUuid = '';
  linkRfc = '';

  private lastLoadedId: number | null = null;

  constructor(private cfdi: CfdiService) {}

  ngOnChanges(): void {
    if (this.orderId && this.orderId !== this.lastLoadedId) {
      this.lastLoadedId = this.orderId;
      this.load();
    }
  }

  load(): void {
    this.loading = true;
    this.resetState();
    this.cfdi
      .getOrderDocument(this.orderId)
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: (doc) => (this.doc = doc),
        error: () => (this.doc = null), // 404 => no document yet
      });
  }

  stamp(): void {
    if (this.working) return;
    this.working = true;
    this.resetState();
    this.cfdi
      .stampOrder(this.orderId)
      .pipe(finalize(() => (this.working = false)))
      .subscribe({
        next: (doc) => (this.doc = doc),
        error: (err: HttpErrorResponse) => {
          const code = err?.error?.code;
          if (err?.status === 409) {
            // Channel issues its own CFDI → offer the link path.
            this.marketplaceHandled = true;
            this.showLink = true;
          } else if (code === 'apiErrors.cfdi.issuerNotConfigured') {
            this.issuerMissing = true;
          } else {
            this.errorKey = 'orders.cfdi.stampError';
          }
        },
      });
  }

  link(): void {
    const uuid = this.linkUuid.trim();
    if (!uuid || this.working) return;
    this.working = true;
    this.errorKey = null;
    this.cfdi
      .linkExternal(this.orderId, uuid, this.linkRfc.trim() || undefined)
      .pipe(finalize(() => (this.working = false)))
      .subscribe({
        next: (doc) => {
          this.doc = doc;
          this.showLink = false;
          this.linkUuid = '';
          this.linkRfc = '';
        },
        error: () => (this.errorKey = 'orders.cfdi.linkError'),
      });
  }

  toggleLink(): void {
    this.showLink = !this.showLink;
  }

  private resetState(): void {
    this.marketplaceHandled = false;
    this.issuerMissing = false;
    this.errorKey = null;
  }
}
