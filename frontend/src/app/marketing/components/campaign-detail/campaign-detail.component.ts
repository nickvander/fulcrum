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
  templateUrl: './campaign-detail.component.html',
  styleUrls: ['./campaign-detail.component.scss']
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
