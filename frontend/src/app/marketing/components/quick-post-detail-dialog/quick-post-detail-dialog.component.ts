import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { MarketingService, CampaignEvent, CampaignEventUpdate } from '../../services/marketing.service';
import { ProductDetailsDialogComponent } from '../../../products/components/product-details-dialog/product-details-dialog.component';
import { ProductService } from '../../../products/services/product';

@Component({
  selector: 'app-quick-post-detail-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatChipsModule,
    MatDividerModule,
    MatSnackBarModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './quick-post-detail-dialog.component.html',
  styleUrls: ['./quick-post-detail-dialog.component.scss']
})
export class QuickPostDetailDialogComponent {
  post: CampaignEvent;
  isEditing = false;
  saving = false;
  publishing = false;
  editForm: FormGroup;

  constructor(
    public dialogRef: MatDialogRef<QuickPostDetailDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { post: CampaignEvent },
    private fb: FormBuilder,
    private marketingService: MarketingService,
    private productService: ProductService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {
    this.post = data.post;
    this.editForm = this.fb.group({
      name: [this.post.name],
      content_subject: [this.post.content_subject],
      content_body: [this.post.content_body],
      content_image_url: [this.post.content_image_url]
    });
  }

  getChannelIcon(channel: string): string {
    const icons: Record<string, string> = {
      email: 'email',
      social: 'share',
      facebook: 'thumb_up',
      instagram: 'camera_alt',
      tiktok: 'play_circle',
      twitter: 'tag'
    };
    return icons[channel] || 'campaign';
  }

  getChannelName(channel: string): string {
    const names: Record<string, string> = {
      email: 'Email',
      social: 'Social',
      facebook: 'Facebook',
      instagram: 'Instagram',
      tiktok: 'TikTok',
      twitter: 'Twitter/X'
    };
    return names[channel] || channel;
  }

  onClose(): void {
    this.dialogRef.close();
  }

  startEdit(): void {
    this.isEditing = true;
    this.editForm.patchValue({
      name: this.post.name,
      content_subject: this.post.content_subject,
      content_body: this.post.content_body,
      content_image_url: this.post.content_image_url
    });
  }

  cancelEdit(): void {
    this.isEditing = false;
  }

  saveChanges(): void {
    this.saving = true;
    const update: CampaignEventUpdate = this.editForm.value;

    this.marketingService.updateEvent(this.post.id, update).subscribe({
      next: (updated) => {
        this.post = { ...this.post, ...updated };
        this.saving = false;
        this.isEditing = false;
        this.snackBar.open('Post updated', 'Close', { duration: 2000 });
      },
      error: (err) => {
        this.saving = false;
        console.error('Failed to update', err);
        this.snackBar.open('Failed to update post', 'Close', { duration: 3000 });
      }
    });
  }

  publishPost(): void {
    if (!this.post.connector_id) {
      this.snackBar.open('No connector configured. Set up a connector first.', 'Close', { duration: 4000 });
      return;
    }

    this.publishing = true;
    this.marketingService.publishEvent(this.post.id).subscribe({
      next: (result) => {
        this.publishing = false;
        this.post.status = 'published';
        this.post.external_id = result.external_id;
        this.post.external_url = result.external_url;
        this.snackBar.open('Post published successfully!', 'View', { duration: 3000 });
      },
      error: (err) => {
        this.publishing = false;
        console.error('Publish failed', err);
        this.snackBar.open('Failed to publish: ' + (err.error?.detail || 'Unknown error'), 'Close', { duration: 4000 });
      }
    });
  }

  openProductDialog(product: any): void {
    this.productService.getProductById(product.id).subscribe({
      next: (fullProduct) => {
        this.dialog.open(ProductDetailsDialogComponent, {
          data: { product: fullProduct, mode: 'view' },
          width: '1000px',
          maxWidth: '95vw',
          maxHeight: '90vh'
        });
      },
      error: (err) => console.error('Failed to load product', err)
    });
  }
}
