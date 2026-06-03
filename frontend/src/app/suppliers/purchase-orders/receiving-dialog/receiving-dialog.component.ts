import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialog, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { FormBuilder, FormGroup, FormArray, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { PurchaseOrder, PurchaseOrderItem } from '../../../shared/models/purchase-order.model';
import { SuppliersService } from '../../suppliers.service';
import { NotificationService } from '../../../core/services/notification.service';
import { QuantityStepperComponent } from '../../../shared/components/quantity-stepper/quantity-stepper.component';

@Component({
    selector: 'app-receiving-dialog',
    templateUrl: './receiving-dialog.component.html',
    styleUrls: ['./receiving-dialog.component.scss'],
    standalone: true,
    imports: [
        CommonModule,
        ReactiveFormsModule,
        MatDialogModule,
        MatButtonModule,
        MatFormFieldModule,
        MatInputModule,
        MatIconModule,
        MatDividerModule,
        TranslocoModule,
        QuantityStepperComponent
    ]
})
export class ReceivingDialogComponent implements OnInit {
    receivingForm: FormGroup;
    po: PurchaseOrder;
    mode: 'receive' | 'correct';

    submitting = false;

    constructor(
        private fb: FormBuilder,
        private suppliersService: SuppliersService,
        private transloco: TranslocoService,
        private notification: NotificationService,
        private dialog: MatDialog,
        public dialogRef: MatDialogRef<ReceivingDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: { po: PurchaseOrder, mode?: 'receive' | 'correct' }
    ) {
        this.po = data.po;
        this.mode = data.mode || 'receive';
        this.receivingForm = this.fb.group({
            reason: [this.transloco.translate('purchaseOrders.receivingDialog.correctionDefaultReason')],
            items: this.fb.array([])
        });
    }

    ngOnInit(): void {
        this.initFormItems();
    }

    get items(): FormArray {
        return this.receivingForm.get('items') as FormArray;
    }

    initFormItems() {
        this.po.items.forEach(item => {
            // Only show items that are not fully received? 
            // Or show all to allow correction/over-receiving?
            // Let's show all but default to remaining quantity.

            const remaining = Math.max(0, item.quantity_ordered - (item.quantity_received || 0));

            this.items.push(this.fb.group({
                po_item_id: [item.id || null],
                product_id: [item.product_id],
                variant_id: [item.variant_id || null],
                variant_name: [item.variant?.name || null],
                variant_sku: [item.variant?.sku || null],
                product_name: [item.product?.name || item.product_name || `Product #${item.product_id}`],
                quantity_ordered: [item.quantity_ordered],
                quantity_received_so_far: [item.quantity_received || 0],
                quantity_to_receive: [this.mode === 'receive' ? remaining : 0, [Validators.min(0)]]
            }));
        });
    }

    title(): string {
        return this.mode === 'correct'
            ? this.transloco.translate('purchaseOrders.receivingDialog.titleCorrect', { id: this.po.id })
            : this.transloco.translate('purchaseOrders.receivingDialog.titleReceive', { id: this.po.id });
    }

    quantityLabel(): string {
        return this.mode === 'correct'
            ? this.transloco.translate('purchaseOrders.receivingDialog.quantityLabelReverse')
            : this.transloco.translate('purchaseOrders.receivingDialog.quantityLabelReceive');
    }

    submitLabel(): string {
        return this.mode === 'correct'
            ? this.transloco.translate('purchaseOrders.receivingDialog.submitCorrect')
            : this.transloco.translate('purchaseOrders.receivingDialog.submitReceive');
    }

    getImageUrl(product: any): string | null {
        if (!product || !product.images || product.images.length === 0) return null;

        // Find primary or first image
        const imgObj = product.images.find((img: any) => img.is_primary) || product.images[0];
        const path = typeof imgObj === 'string' ? imgObj : imgObj.image_path || imgObj.url;

        if (!path) return null;
        if (path.startsWith('http')) return path;
        if (path.startsWith('assets')) return path;

        // Normalize path
        let cleanPath = path.startsWith('/') ? path.substring(1) : path;

        // If it's in uploads directory
        if (cleanPath.startsWith('uploads')) {
            return `/${cleanPath}`;
        }

        // If it looks like a filename, assume product_images
        if (!cleanPath.includes('/')) {
            return `/uploads/product_images/${cleanPath}`;
        }

        return path;
    }

    getVariantName(item: PurchaseOrderItem): string | null {
        if (!item.variant_id || !item.product?.variants?.length) return null;
        return item.product.variants.find((variant: any) => variant.id === item.variant_id)?.name || null;
    }

    getVariantSku(item: PurchaseOrderItem): string | null {
        if (!item.variant_id || !item.product?.variants?.length) return null;
        return item.product.variants.find((variant: any) => variant.id === item.variant_id)?.sku || null;
    }

    onCancel(): void {
        this.dialogRef.close();
    }

    /** Open the camera/keyboard scanner and apply the scanned code to a line. */
    openScanner(): void {
        import('../../../inventory-count/components/scan-sku-dialog/scan-sku-dialog.component').then(
            ({ ScanSkuDialogComponent }) => {
                const ref = this.dialog.open(ScanSkuDialogComponent, { width: '420px' });
                ref.afterClosed().subscribe((code: string | undefined) => {
                    if (code) this.applyScannedCode(code);
                });
            },
        );
    }

    /**
     * Match a scanned SKU/barcode to a PO line and bump its receive qty by one.
     * Returns true when a line matched. Pure enough to unit-test directly.
     */
    applyScannedCode(code: string): boolean {
        const norm = (code || '').trim().toLowerCase();
        if (!norm) return false;
        for (let i = 0; i < this.items.length; i++) {
            const p = this.po.items[i]?.product as any;
            const ctrl = this.items.at(i);
            const candidates = [
                p?.sku,
                p?.barcode_value,
                p?.qrcode_value,
                ctrl.get('variant_sku')?.value,
            ]
                .filter((s): s is string => !!s)
                .map(s => s.toLowerCase());
            if (candidates.includes(norm)) {
                const cur = Number(ctrl.get('quantity_to_receive')?.value) || 0;
                ctrl.get('quantity_to_receive')?.setValue(cur + 1);
                this.notification.showSuccess(
                    this.transloco.translate('purchaseOrders.receivingDialog.scanAdded', {
                        name: ctrl.get('product_name')?.value,
                    }),
                );
                return true;
            }
        }
        this.notification.showError(
            this.transloco.translate('purchaseOrders.receivingDialog.scanNoMatch', { code }),
        );
        return false;
    }

    /** i18n key for the destination warehouse stock lands in (the local Bodega). */
    destinationLabelKey(): string {
        return 'products.bucketDefault';
    }

    /** Total units about to be received across all lines. */
    totalToReceive(): number {
        return this.items.controls.reduce(
            (sum, c) => sum + (Number(c.get('quantity_to_receive')?.value) || 0),
            0,
        );
    }

    /** True when any line will receive MORE than was ordered (needs a reason). */
    hasOverReceipt(): boolean {
        return this.items.controls.some((c) => {
            const ordered = Number(c.get('quantity_ordered')?.value) || 0;
            const soFar = Number(c.get('quantity_received_so_far')?.value) || 0;
            const toReceive = Number(c.get('quantity_to_receive')?.value) || 0;
            return soFar + toReceive > ordered;
        });
    }

    /** Over-receipt is allowed, but only with a reason on record. */
    blockedByExceedReason(): boolean {
        return this.mode !== 'correct' && this.hasOverReceipt() && !this.receivingForm.get('reason')?.value?.trim();
    }

    /** True when at least one line still has remaining (un-received) quantity. */
    hasRemaining(): boolean {
        return this.items.controls.some((c) => {
            const ordered = Number(c.get('quantity_ordered')?.value) || 0;
            const soFar = Number(c.get('quantity_received_so_far')?.value) || 0;
            return ordered - soFar > 0;
        });
    }

    /** P0-2: one-tap "receive everything still outstanding", then submit. */
    receiveAll(): void {
        this.items.controls.forEach((c) => {
            const ordered = Number(c.get('quantity_ordered')?.value) || 0;
            const soFar = Number(c.get('quantity_received_so_far')?.value) || 0;
            c.get('quantity_to_receive')?.setValue(Math.max(0, ordered - soFar));
        });
        this.onSubmit();
    }

    onSubmit(): void {
        if (!this.receivingForm.valid || this.submitting) return;

        // P1: over-receipt must carry a reason.
        if (this.blockedByExceedReason()) {
            this.notification.showError(
                this.transloco.translate('purchaseOrders.receivingDialog.exceedReasonRequired'),
            );
            return;
        }

        const formValue = this.receivingForm.value;
        // A reason is attached for corrections AND for over-receipt receives.
        const attachReason = this.mode === 'correct' || this.hasOverReceipt();
        const itemsToSubmit = formValue.items
            .filter((item: any) => item.quantity_to_receive > 0)
            .map((item: any) => ({
                po_item_id: item.po_item_id,
                product_id: item.product_id,
                variant_id: item.variant_id,
                quantity: item.quantity_to_receive,
                reason: attachReason ? formValue.reason : undefined
            }));

        if (itemsToSubmit.length === 0) {
            this.dialogRef.close();
            return;
        }

        const total = itemsToSubmit.reduce((sum: number, i: any) => sum + i.quantity, 0);
        this.submitting = true;

        const request$ = this.mode === 'correct'
            ? this.suppliersService.correctReceivedPurchaseOrderItems(this.po.id, itemsToSubmit)
            : this.suppliersService.receivePurchaseOrderItems(this.po.id, itemsToSubmit);

        request$.subscribe({
            next: (updatedPo) => {
                this.submitting = false;
                // P0-1: explicit success toast that NAMES the destination warehouse.
                if (this.mode !== 'correct') {
                    this.notification.showSuccess(
                        this.transloco.translate('purchaseOrders.receivingDialog.successAdded', {
                            n: total,
                            location: this.transloco.translate(this.destinationLabelKey()),
                        }),
                    );
                }
                this.dialogRef.close(updatedPo);
            },
            error: (err) => {
                console.error('Error receiving items:', err);
                this.submitting = false;
                // P0-1: surface a real error toast and KEEP the dialog open so nothing
                // is silently lost — the operator can retry.
                this.notification.showError(
                    this.transloco.translate('purchaseOrders.receivingDialog.errorReceiving'),
                );
            }
        });
    }
}
