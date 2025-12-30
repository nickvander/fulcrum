import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatTabsModule } from '@angular/material/tabs';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatListModule } from '@angular/material/list';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';

import { MarketingService, Campaign, CampaignProductSummary } from '../../services/marketing.service';
import { ProductService } from '../../../products/services/product';
import { ProductDetailsDialogComponent } from '../../../products/components/product-details-dialog/product-details-dialog.component';

@Component({
  selector: 'app-campaign-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatTabsModule,
    MatProgressSpinnerModule,
    MatListModule,
    MatDialogModule
  ],
  template: `
    <div class="campaign-detail-container" *ngIf="campaign">
      <!-- Header -->
      <div class="header-actions">
        <button mat-icon-button routerLink="/marketing">
          <mat-icon>arrow_back</mat-icon>
        </button>
        <div class="header-title">
          <h1>{{ campaign.name }}</h1>
          <span class="status-chip" [class]="campaign.status">{{ campaign.status | titlecase }}</span>
        </div>
        <div class="spacer"></div>
        <button mat-stroked-button color="primary">Edit</button>
      </div>

      <div class="content-grid">
        <!-- Main Info -->
        <div class="main-column">
          <mat-card class="mb-4">
            <mat-card-header>
              <mat-card-title>Overview</mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <p class="description">{{ campaign.description || 'No description provided.' }}</p>
              
              <div class="stats-grid">
                <div class="stat-item">
                  <span class="label">Budget</span>
                  <span class="value">{{ campaign.budget | currency }}</span>
                </div>
                <div class="stat-item">
                  <span class="label">Spent</span>
                  <span class="value">{{ campaign.spent | currency }}</span>
                </div>
                <div class="stat-item">
                  <span class="label">Events</span>
                  <span class="value">{{ campaign.events.length }}</span>
                </div>
              </div>
            </mat-card-content>
          </mat-card>

          <!-- Events -->
          <h3>Events</h3>
          <mat-card *ngFor="let event of campaign.events" class="event-card mb-2">
            <div class="event-row">
              <mat-icon [class]="event.channel_type">{{ getChannelIcon(event.channel_type) }}</mat-icon>
              <div class="event-info">
                <h4>{{ event.name }}</h4>
                <p class="secondary-text">{{ event.scheduled_at | date:'medium' }}</p>
              </div>
              <span class="status-badge" [class]="event.status">{{ event.status }}</span>
            </div>
            <div class="event-content" *ngIf="event.content_body">
                <p>{{ event.content_body }}</p>
                <img *ngIf="event.content_image_url" [src]="event.content_image_url" class="event-img">
            </div>
          </mat-card>
        </div>

        <!-- Sidebar -->
        <div class="sidebar">
          <!-- Products -->
          <mat-card class="mb-4">
            <mat-card-header>
              <mat-card-title>Linked Products</mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <div class="product-list" *ngIf="campaign.products?.length; else noProducts">
                <div *ngFor="let product of campaign.products" 
                   (click)="openProductDialog(product)"
                   class="product-item clickable">
                  <img [src]="product.image_url" onerror="this.src='assets/placeholder.jpg'">
                  <div class="product-info">
                    <span class="product-name">{{ product.name }}</span>
                    <span class="product-sku">{{ product.sku }}</span>
                  </div>
                  <mat-icon>visibility</mat-icon>
                </div>
              </div>
              <ng-template #noProducts>
                <p class="secondary-text">No products linked.</p>
              </ng-template>
            </mat-card-content>
          </mat-card>
        </div>
      </div>
    </div>

    <div class="loading-container" *ngIf="loading">
      <mat-spinner></mat-spinner>
    </div>
  `,
  styles: [`
    .campaign-detail-container {
      padding: 24px;
      max-width: 1200px;
      margin: 0 auto;
    }
    .header-actions {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 24px;
    }
    .header-title {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .header-title h1 { margin: 0; font-size: 24px; }
    .status-chip {
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 12px;
        text-transform: uppercase;
        font-weight: 500;
    }
    .status-chip.draft { background: #e3f2fd; color: #1976d2; }
    .status-chip.active { background: #e8f5e9; color: #2e7d32; }
    .spacer { flex: 1; }
    
    .content-grid {
        display: grid;
        grid-template-columns: 2fr 1fr;
        gap: 24px;
    }
    @media (max-width: 768px) {
        .content-grid { grid-template-columns: 1fr; }
    }

    .stats-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid #eee;
    }
    .stat-item {
        display: flex;
        flex-direction: column;
    }
    .stat-item .label { font-size: 12px; color: #666; }
    .stat-item .value { font-size: 18px; font-weight: 500; }

    .event-card { padding: 16px; }
    .event-row { display: flex; align-items: center; gap: 16px; }
    .event-info { flex: 1; }
    .event-info h4 { margin: 0; font-weight: 500; }
    .secondary-text { margin: 0; color: #666; font-size: 12px; }
    .event-img { max-height: 100px; margin-top: 8px; border-radius: 4px; }
    .event-content { margin-top: 12px; padding-top: 12px; border-top: 1px solid #eee; }

    .product-list { display: flex; flex-direction: column; gap: 8px; }
    .product-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px;
        border-radius: 8px;
        text-decoration: none;
        color: inherit;
        background: #f9f9f9;
        transition: background 0.2s;
    }
    .product-item:hover { background: #eee; }
    .product-item.clickable { cursor: pointer; }
    .product-item img { width: 40px; height: 40px; border-radius: 4px; object-fit: cover; }
    .product-info { flex: 1; display: flex; flex-direction: column; }
    .product-name { font-weight: 500; font-size: 14px; }
    .product-sku { font-size: 12px; color: #666; }
    
    .mb-4 { margin-bottom: 24px; }
    .mb-2 { margin-bottom: 12px; }
    .loading-container { display: flex; justify-content: center; padding: 48px; }
  `]
})
export class CampaignDetailComponent implements OnInit {
  campaign: Campaign | null = null;
  loading = true;

  constructor(
    private route: ActivatedRoute,
    private marketingService: MarketingService,
    private productService: ProductService,
    private dialog: MatDialog
  ) { }

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.marketingService.getCampaign(+id).subscribe({
        next: (data) => {
          this.campaign = data;
          this.loading = false;
        },
        error: (err) => {
          console.error(err);
          this.loading = false;
        }
      });
    }
  }

  getChannelIcon(channel: string): string {
    // ... logic
    return 'campaign';
  }

  openProductDialog(product: CampaignProductSummary): void {
    // Fetch full product data before opening dialog
    this.productService.getProductById(product.id).subscribe({
      next: (fullProduct) => {
        this.dialog.open(ProductDetailsDialogComponent, {
          data: { product: fullProduct, mode: 'view' },
          width: '1000px',
          maxWidth: '95vw',
          maxHeight: '90vh',
          panelClass: 'product-details-dialog-panel'
        });
      },
      error: (err) => console.error('Failed to load product', err)
    });
  }
}
