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
  template: `
    <div class="quick-post-detail-dialog">
      <!-- Header -->
      <header class="dialog-header" [ngClass]="'channel-' + post.channel_type">
        <div class="channel-badge">
          <mat-icon>{{ getChannelIcon(post.channel_type) }}</mat-icon>
          <span>{{ getChannelName(post.channel_type) }}</span>
        </div>
        <mat-chip [ngClass]="'status-' + post.status">{{ post.status | titlecase }}</mat-chip>
      </header>

      <mat-dialog-content>
        <!-- View Mode -->
        <div *ngIf="!isEditing" class="view-mode">
          <h2 class="post-title">{{ post.name || 'Untitled Post' }}</h2>
          
          <!-- Email Subject -->
          <div class="field-group" *ngIf="post.content_subject">
            <label>Subject</label>
            <p class="subject-line">{{ post.content_subject }}</p>
          </div>

          <!-- Content -->
          <div class="field-group">
            <label>Content</label>
            <p class="content-body">{{ post.content_body || 'No content' }}</p>
          </div>

          <!-- Image -->
          <div class="field-group" *ngIf="post.content_image_url">
            <label>Image</label>
            <img [src]="post.content_image_url" class="post-image" onerror="this.style.display='none'">
          </div>

          <!-- Linked Products -->
          <div class="field-group" *ngIf="post.products && post.products.length > 0">
            <label>Linked Products</label>
            <div class="products-list">
              <div class="product-chip" *ngFor="let product of post.products" (click)="openProductDialog(product)">
                <img [src]="product.image_url || 'assets/placeholder.jpg'" onerror="this.src='assets/placeholder.jpg'">
                <span>{{ product.name }}</span>
              </div>
            </div>
          </div>

          <mat-divider></mat-divider>

          <!-- Metadata -->
          <div class="metadata">
            <div class="meta-item">
              <mat-icon>schedule</mat-icon>
              <span>Created: {{ post.created_at | date:'medium' }}</span>
            </div>
            <div class="meta-item" *ngIf="post.published_at">
              <mat-icon>check_circle</mat-icon>
              <span>Published: {{ post.published_at | date:'medium' }}</span>
            </div>
            <div class="meta-item" *ngIf="post.external_url">
              <mat-icon>link</mat-icon>
              <a [href]="post.external_url" target="_blank">View on {{ getChannelName(post.channel_type) }}</a>
            </div>
            <div class="meta-item error" *ngIf="post.error_message">
              <mat-icon>error</mat-icon>
              <span>{{ post.error_message }}</span>
            </div>
          </div>
        </div>

        <!-- Edit Mode -->
        <form *ngIf="isEditing" [formGroup]="editForm" class="edit-mode">
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Post Name</mat-label>
            <input matInput formControlName="name" placeholder="Give your post a name">
          </mat-form-field>

          <mat-form-field appearance="outline" class="full-width" *ngIf="post.channel_type === 'email'">
            <mat-label>Subject Line</mat-label>
            <input matInput formControlName="content_subject">
          </mat-form-field>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Content</mat-label>
            <textarea matInput formControlName="content_body" rows="6"></textarea>
          </mat-form-field>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Image URL</mat-label>
            <input matInput formControlName="content_image_url" placeholder="https://...">
          </mat-form-field>
        </form>
      </mat-dialog-content>

      <mat-dialog-actions align="end">
        <button mat-button (click)="onClose()">Close</button>
        
        <!-- View Mode Actions -->
        <ng-container *ngIf="!isEditing">
          <button mat-stroked-button (click)="startEdit()">
            <mat-icon>edit</mat-icon> Edit
          </button>
          <button mat-raised-button color="primary" 
                  *ngIf="post.status === 'draft'" 
                  [disabled]="publishing"
                  (click)="publishPost()">
            <mat-spinner diameter="18" *ngIf="publishing"></mat-spinner>
            <mat-icon *ngIf="!publishing">send</mat-icon>
            {{ publishing ? 'Publishing...' : 'Publish' }}
          </button>
        </ng-container>

        <!-- Edit Mode Actions -->
        <ng-container *ngIf="isEditing">
          <button mat-stroked-button (click)="cancelEdit()">Cancel</button>
          <button mat-raised-button color="primary" [disabled]="saving" (click)="saveChanges()">
            <mat-spinner diameter="18" *ngIf="saving"></mat-spinner>
            {{ saving ? 'Saving...' : 'Save Changes' }}
          </button>
        </ng-container>
      </mat-dialog-actions>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }

    .quick-post-detail-dialog {
      width: 100%;
      overflow: hidden;
    }

    ::ng-deep .mat-mdc-dialog-container .mdc-dialog__content {
      padding-top: 0 !important;
    }

    .dialog-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 24px;
      margin: 0 !important;
      color: white;
      border-radius: 0;
      font-weight: 500;
      font-size: 1.25rem;
      width: 100%;
      box-sizing: border-box;
    }

    .channel-email { background: linear-gradient(135deg, #667eea, #764ba2); }
    .channel-social { background: linear-gradient(135deg, #f093fb, #f5576c); }
    .channel-facebook { background: #1877f2; }
    .channel-instagram { background: linear-gradient(135deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888); }
    .channel-tiktok { background: #000; }
    .channel-twitter { background: #1da1f2; }

    .channel-badge {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 500;
    }

    .channel-badge mat-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
    }

    .status-draft { background: #e3f2fd !important; color: #1565c0 !important; }
    .status-published { background: #e8f5e9 !important; color: #2e7d32 !important; }
    .status-failed { background: #ffebee !important; color: #c62828 !important; }
    .status-scheduled { background: #fff3e0 !important; color: #e65100 !important; }

    .post-title {
      margin: 0 0 16px;
      font-size: 20px;
      font-weight: 500;
    }

    .field-group {
      margin-bottom: 16px;
    }

    .field-group label {
      display: block;
      font-size: 12px;
      color: #666;
      margin-bottom: 4px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .subject-line {
      font-weight: 500;
      margin: 0;
    }

    .content-body {
      margin: 0;
      white-space: pre-wrap;
      line-height: 1.6;
    }

    .post-image {
      max-width: 100%;
      max-height: 200px;
      border-radius: 8px;
      object-fit: cover;
    }

    .products-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .product-chip {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 4px 12px 4px 4px;
      background: #f5f5f5;
      border-radius: 20px;
      cursor: pointer;
      transition: background 0.2s;
    }

    .product-chip:hover {
      background: #e0e0e0;
    }

    .product-chip img {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      object-fit: cover;
    }

    .product-chip span {
      font-size: 13px;
    }

    mat-divider {
      margin: 16px 0;
    }

    .metadata {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .meta-item {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: #666;
    }

    .meta-item mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }

    .meta-item.error {
      color: #c62828;
    }

    .meta-item a {
      color: #1976d2;
    }

    .full-width {
      width: 100%;
    }

    .edit-mode {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    mat-dialog-actions button mat-icon {
      margin-right: 4px;
    }

    mat-dialog-actions mat-spinner {
      display: inline-block;
      margin-right: 8px;
    }
  `]
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
