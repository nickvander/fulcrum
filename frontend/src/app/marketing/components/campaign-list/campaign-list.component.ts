import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatCardModule } from '@angular/material/card';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressBarModule } from '@angular/material/progress-bar'; // Added this import

import { MarketingService, CampaignSummary, CampaignEvent } from '../../services/marketing.service';
import { DateRangePresetsComponent } from '../../../shared/components/date-range-presets/date-range-presets.component';
import { StatusFilterComponent, StatusFilterOption } from '../../../shared/components/status-filter/status-filter.component';
import { DateRange } from '../../../shared/services/date-range.service';

import { QuickPostDialogComponent } from '../quick-post-dialog/quick-post-dialog.component';
import { QuickPostDetailDialogComponent } from '../quick-post-detail-dialog/quick-post-detail-dialog.component';

@Component({
  selector: 'app-campaign-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatDialogModule,
    MatSnackBarModule,
    MatCardModule,
    MatTooltipModule,
    MatProgressBarModule,
    DateRangePresetsComponent,
    StatusFilterComponent
  ],
  template: `
    <div class="campaign-list-container">
      <!-- Header -->
      <div class="marketing-header">
        <div class="title-section">
          <h1>Marketing</h1>
          <p class="subtitle">Campaigns & Events</p>
        </div>
        <div class="actions-section">
          <!-- Calendar Toggle -->
          <a mat-icon-button color="accent" routerLink="/marketing/calendar" matTooltip="Calendar View">
             <mat-icon>calendar_month</mat-icon>
          </a>
          
          <!-- Connectors -->
          <a mat-stroked-button routerLink="/marketing/connectors">
             <mat-icon>settings_input_component</mat-icon> Connectors
          </a>

          <!-- Quick Post -->
          <button mat-stroked-button color="primary" (click)="openQuickPostDialog()">
             <mat-icon>bolt</mat-icon> Quick Post
          </button>

          <!-- New Campaign -->
          <a mat-flat-button color="primary" routerLink="/marketing/new">
             <mat-icon>add</mat-icon> New Campaign
          </a>
        </div>
      </div>

      <!-- KPI Cards -->
      <div class="kpi-cards">
        <mat-card class="kpi-card">
          <mat-card-content>
            <div class="kpi-value">{{ campaigns.length }}</div>
            <div class="kpi-label">Total Campaigns</div>
          </mat-card-content>
        </mat-card>
        <mat-card class="kpi-card active">
          <mat-card-content>
            <div class="kpi-value">{{ getActiveCount() }}</div>
            <div class="kpi-label">Active</div>
          </mat-card-content>
        </mat-card>
        <mat-card class="kpi-card scheduled">
          <mat-card-content>
            <div class="kpi-value">{{ getScheduledCount() }}</div>
            <div class="kpi-label">Scheduled</div>
          </mat-card-content>
        </mat-card>
        <mat-card class="kpi-card draft">
          <mat-card-content>
            <div class="kpi-value">{{ getDraftCount() }}</div>
            <div class="kpi-label">Drafts</div>
          </mat-card-content>
        </mat-card>
      </div>

      <!-- Filters Toolbar -->
      <div class="filters-toolbar">
        <app-date-range-presets 
          [useGlobalService]="false" 
          [showAllOption]="true"
          [defaultPreset]="'all'"
          (rangeChange)="onDateRangeChange($event)">
        </app-date-range-presets>
        <app-status-filter 
          [options]="statusOptions" 
          [selectedValue]="statusFilter"
          (valueChange)="setStatusFilter($event)">
        </app-status-filter>
      </div>

      <!-- Loading Spinner -->
      <div class="loading-container" *ngIf="loading">
        <mat-spinner diameter="40"></mat-spinner>
      </div>

      <!-- Campaign Section Header -->
      <div class="section-header" *ngIf="!loading">
        <h2>Campaigns</h2>
        <span class="result-count">{{ filteredCampaigns.length }} result{{ filteredCampaigns.length !== 1 ? 's' : '' }}</span>
      </div>

      <!-- Campaign Table -->
      <mat-card class="campaigns-table-card" *ngIf="!loading">
        <table mat-table [dataSource]="filteredCampaigns" class="campaigns-table">
          <!-- Name Column -->
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef>Campaign</th>
            <td mat-cell *matCellDef="let campaign">
              <a [routerLink]="[campaign.id]" class="campaign-link">
                {{ campaign.name }}
              </a>
            </td>
          </ng-container>

          <!-- Status Column -->
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let campaign">
              <mat-chip [ngClass]="'status-' + campaign.status">
                {{ campaign.status | titlecase }}
              </mat-chip>
            </td>
          </ng-container>

          <!-- Dates Column -->
          <ng-container matColumnDef="dates">
            <th mat-header-cell *matHeaderCellDef>Dates</th>
            <td mat-cell *matCellDef="let campaign">
              <span *ngIf="campaign.start_date; else noDates">
                {{ campaign.start_date | date:'mediumDate' }}
                <span *ngIf="campaign.end_date"> - {{ campaign.end_date | date:'mediumDate' }}</span>
              </span>
              <ng-template #noDates>
                <span class="no-date">Not scheduled</span>
              </ng-template>
            </td>
          </ng-container>

          <!-- Events Column -->
          <ng-container matColumnDef="events">
            <th mat-header-cell *matHeaderCellDef>Events</th>
            <td mat-cell *matCellDef="let campaign">
              <span class="event-count">{{ campaign.events_count }}</span>
            </td>
          </ng-container>

          <!-- Products Column -->
          <ng-container matColumnDef="products">
            <th mat-header-cell *matHeaderCellDef>Products</th>
            <td mat-cell *matCellDef="let campaign">
              <span class="product-count">{{ campaign.products_count }}</span>
            </td>
          </ng-container>

          <!-- Actions Column -->
          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef></th>
            <td mat-cell *matCellDef="let campaign">
              <button mat-icon-button [matMenuTriggerFor]="menu">
                <mat-icon>more_vert</mat-icon>
              </button>
              <mat-menu #menu="matMenu">
                <button mat-menu-item [routerLink]="[campaign.id]">
                  <mat-icon>visibility</mat-icon>
                  <span>View Details</span>
                </button>
                <button mat-menu-item [routerLink]="[campaign.id, 'edit']">
                  <mat-icon>edit</mat-icon>
                  <span>Edit</span>
                </button>
                <button mat-menu-item (click)="duplicateCampaign(campaign)">
                  <mat-icon>content_copy</mat-icon>
                  <span>Duplicate</span>
                </button>
                <button mat-menu-item class="delete-action" (click)="deleteCampaign(campaign)">
                  <mat-icon>delete</mat-icon>
                  <span>Delete</span>
                </button>
              </mat-menu>
            </td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
        </table>

        <!-- Empty State -->
        <div class="empty-state" *ngIf="campaigns.length === 0">
          <mat-icon>campaign</mat-icon>
          <h3>No campaigns yet</h3>
          <p>Create your first marketing campaign to get started</p>
          <button mat-raised-button color="primary" routerLink="new">
            <mat-icon>add</mat-icon>
            Create Campaign
          </button>
        </div>
      </mat-card>

      <!-- Quick Posts Section -->
      <div class="section-header" *ngIf="!loading">
        <h2>Recent Quick Posts</h2>
        <span class="result-count">{{ filteredQuickPosts.length }} result{{ filteredQuickPosts.length !== 1 ? 's' : '' }}</span>
      </div>
      <mat-card class="quick-posts-card" *ngIf="!loading">
        <div class="quick-posts-list" *ngIf="filteredQuickPosts.length > 0; else noQuickPosts">
          <div class="quick-post-item clickable" *ngFor="let post of filteredQuickPosts" (click)="openQuickPostDetail(post)">

            <div class="post-icon" [ngClass]="'channel-' + post.channel_type">
              <mat-icon>{{ getChannelIcon(post.channel_type) }}</mat-icon>
            </div>
            <div class="post-content">
              <div class="post-header">
                <span class="post-name">{{ post.name || 'Untitled Post' }}</span>
                <mat-chip class="post-status" [ngClass]="'status-' + post.status">{{ post.status | titlecase }}</mat-chip>
              </div>
              <p class="post-body" *ngIf="post.content_body">{{ post.content_body | slice:0:100 }}{{ post.content_body.length > 100 ? '...' : '' }}</p>
              <span class="post-date">{{ post.created_at | date:'medium' }}</span>
            </div>
            <button mat-icon-button [matMenuTriggerFor]="postMenu" (click)="$event.stopPropagation()">
              <mat-icon>more_vert</mat-icon>
            </button>
            <mat-menu #postMenu="matMenu">
              <button mat-menu-item (click)="deleteQuickPost(post)">
                <mat-icon>delete</mat-icon>
                <span>Delete</span>
              </button>
            </mat-menu>
          </div>
        </div>
        <ng-template #noQuickPosts>
          <div class="empty-state small">
            <mat-icon>bolt</mat-icon>
            <p>No quick posts yet. Create your first quick post to share content immediately.</p>
          </div>
        </ng-template>
      </mat-card>
    </div>
  `,
  styles: [`
    .campaign-list-container {
      padding: 24px;
      max-width: 1400px;
      margin: 0 auto;
    }

    .marketing-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      flex-wrap: wrap;
      gap: 16px;
    }
    
    .title-section h1 {
        margin: 0;
        font-size: 28px;
        font-weight: 500;
        color: #2c3e50;
    }
    
    .title-section .subtitle {
        margin: 4px 0 0;
        color: #7f8c8d;
    }

    .actions-section {
      display: flex;
      gap: 12px;
      align-items: center;
    }
    
    @media (max-width: 768px) {
      .marketing-header { 
          flex-direction: column; 
          align-items: flex-start; 
      }
      .actions-section { 
          width: 100%; 
          justify-content: flex-start; 
          flex-wrap: wrap;
      }
      .actions-section button, .actions-section a {
          flex: 1;
      }
    }

    .kpi-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }

    .kpi-card {
      text-align: center;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border-radius: 12px;
    }

    .kpi-card.active {
      background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }

    .kpi-card.scheduled {
      background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }

    .kpi-card.draft {
      background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }

    .kpi-value {
      font-size: 32px;
      font-weight: 700;
    }

    .kpi-label {
      font-size: 14px;
      opacity: 0.9;
    }

    .loading-container {
      display: flex;
      justify-content: center;
      padding: 48px;
    }

    .campaigns-table-card {
      border-radius: 12px;
      overflow: hidden;
    }

    .campaigns-table {
      width: 100%;
    }

    .campaign-link {
      color: #1976d2;
      text-decoration: none;
      font-weight: 500;
    }

    .campaign-link:hover {
      text-decoration: underline;
    }

    .status-draft {
      background-color: #e3f2fd !important;
      color: #1565c0 !important;
    }

    .status-scheduled {
      background-color: #fff3e0 !important;
      color: #e65100 !important;
    }

    .status-active {
      background-color: #e8f5e9 !important;
      color: #2e7d32 !important;
    }

    .status-completed {
      background-color: #f3e5f5 !important;
      color: #7b1fa2 !important;
    }

    .status-paused {
      background-color: #fce4ec !important;
      color: #c2185b !important;
    }

    .no-date {
      color: #999;
      font-style: italic;
    }

    .event-count, .product-count {
      background: #e0e0e0;
      padding: 4px 10px;
      border-radius: 12px;
      font-size: 13px;
    }

    .delete-action {
      color: #f44336;
    }

    .empty-state {
      text-align: center;
      padding: 64px 24px;
      color: #666;
    }

    .empty-state mat-icon {
      font-size: 64px;
      width: 64px;
      height: 64px;
      color: #ccc;
    }

    .empty-state h3 {
      margin: 16px 0 8px;
      font-weight: 500;
    }

    .empty-state p {
      margin-bottom: 24px;
    }

    .filters-toolbar {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 16px;
      margin-bottom: 16px;
      padding: 16px;
      background: #fafafa;
      border-radius: 12px;
    }

    .filter-group {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .filter-label {
      font-size: 13px;
      color: #666;
      font-weight: 500;
    }

    .filter-group button.active {
      background: #263238;
      color: white;
      border-color: #263238;
    }

    .filter-group button {
      border-radius: 8px;
      font-size: 0.85rem;
    }

    .filter-count {
      margin-left: auto;
      color: #666;
      font-size: 13px;
      white-space: nowrap;
    }

    @media (max-width: 768px) {
      .filters-toolbar {
        flex-direction: column;
        align-items: stretch;
        gap: 12px;
      }
      .filter-count {
        margin-left: 0;
        text-align: center;
      }
    }

    .section-title {
      margin: 32px 0 16px;
      font-size: 20px;
      font-weight: 500;
    }

    .quick-posts-card {
      border-radius: 12px;
      padding: 16px;
    }

    .quick-posts-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .quick-post-item {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 12px;
      background: #f9f9f9;
      border-radius: 8px;
      transition: background 0.2s, transform 0.1s;
    }

    .quick-post-item.clickable {
      cursor: pointer;
    }

    .quick-post-item.clickable:hover {
      background: #f0f0f0;
      transform: translateX(4px);
    }

    .post-icon {
      width: 40px;
      height: 40px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
    }

    .channel-email { background: linear-gradient(135deg, #667eea, #764ba2); }
    .channel-social { background: linear-gradient(135deg, #f093fb, #f5576c); }
    .channel-facebook { background: #1877f2; }
    .channel-instagram { background: linear-gradient(135deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888); }
    .channel-tiktok { background: #000; }
    .channel-twitter { background: #1da1f2; }

    .post-content {
      flex: 1;
      min-width: 0;
    }

    .post-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;
    }

    .post-name {
      font-weight: 500;
    }

    .post-status {
      font-size: 11px;
      height: 20px;
      min-height: 20px;
    }

    .post-body {
      color: #666;
      margin: 4px 0;
      font-size: 13px;
    }

    .post-date {
      font-size: 12px;
      color: #999;
    }

    .empty-state.small {
      padding: 24px;
    }

    .empty-state.small mat-icon {
      font-size: 32px;
      width: 32px;
      height: 32px;
    }

    .section-header {
      display: flex;
      align-items: baseline;
      gap: 12px;
      margin: 24px 0 12px;
    }

    .section-header h2 {
      margin: 0;
      font-size: 18px;
      font-weight: 500;
      color: #333;
    }

    .result-count {
      font-size: 13px;
      color: #888;
      font-weight: 400;
    }
  `]
})
export class CampaignListComponent implements OnInit {
  campaigns: CampaignSummary[] = [];
  filteredCampaigns: CampaignSummary[] = [];
  quickPosts: CampaignEvent[] = [];
  filteredQuickPosts: CampaignEvent[] = [];
  statusFilter: string = 'all';
  dateRange: DateRange | null = null;  // Start with no date filter for marketing
  loading = true;
  displayedColumns = ['name', 'status', 'dates', 'events', 'products', 'actions'];

  statusOptions: StatusFilterOption[] = [
    { value: 'all', label: 'All' },
    { value: 'draft', label: 'Draft', icon: 'edit_note' },
    { value: 'scheduled', label: 'Scheduled', icon: 'schedule' },
    { value: 'active', label: 'Active', icon: 'play_circle' },
    { value: 'completed', label: 'Done', icon: 'check_circle' }
  ];

  constructor(
    private marketingService: MarketingService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) { }

  ngOnInit(): void {
    this.loadCampaigns();
    this.loadQuickPosts();
  }

  loadCampaigns(): void {
    this.loading = true;
    this.marketingService.getCampaigns().subscribe({
      next: (campaigns) => {
        this.campaigns = campaigns;
        this.applyFilter();
        this.loading = false;
      },
      error: (err) => {
        console.error('Failed to load campaigns', err);
        this.loading = false;
        this.snackBar.open('Failed to load campaigns', 'Close', { duration: 3000 });
      }
    });
  }

  setStatusFilter(status: string): void {
    this.statusFilter = status;
    this.applyFilter();
  }

  applyFilter(): void {
    let filtered = [...this.campaigns];

    // Status filter
    if (this.statusFilter !== 'all') {
      filtered = filtered.filter(c => c.status === this.statusFilter);
    }

    // Date range filter - check if campaign date range OVERLAPS with filter range
    if (this.dateRange) {
      filtered = filtered.filter(c => {
        if (!c.start_date) return true; // Include campaigns without dates

        const campaignStart = new Date(c.start_date);
        const campaignEnd = c.end_date ? new Date(c.end_date) : campaignStart;
        const filterStart = this.dateRange!.startDate;
        const filterEnd = this.dateRange!.endDate;

        // Check for overlap: campaign overlaps if it doesn't end before filter starts
        // and doesn't start after filter ends
        return campaignEnd >= filterStart && campaignStart <= filterEnd;
      });
    }

    this.filteredCampaigns = filtered;

    // Filter quick posts by status and date
    let filteredPosts = [...this.quickPosts];

    // Status filter for quick posts (map campaign statuses to event statuses)
    if (this.statusFilter !== 'all') {
      filteredPosts = filteredPosts.filter(p => p.status === this.statusFilter);
    }

    // Date range filter for quick posts
    if (this.dateRange) {
      filteredPosts = filteredPosts.filter(p => {
        if (!p.created_at) return true;
        const postDate = new Date(p.created_at);
        return postDate >= this.dateRange!.startDate && postDate <= this.dateRange!.endDate;
      });
    }

    this.filteredQuickPosts = filteredPosts;
  }

  onDateRangeChange(range: DateRange | null): void {
    this.dateRange = range;
    this.applyFilter();
  }

  clearDateFilter(): void {
    this.dateRange = null;
    this.applyFilter();
  }

  getActiveCount(): number {
    return this.campaigns.filter(c => c.status === 'active').length;
  }

  getScheduledCount(): number {
    return this.campaigns.filter(c => c.status === 'scheduled').length;
  }

  getDraftCount(): number {
    return this.campaigns.filter(c => c.status === 'draft').length;
  }

  duplicateCampaign(campaign: CampaignSummary): void {
    // TODO: Implement duplicate
    this.snackBar.open('Duplicate feature coming soon', 'Close', { duration: 2000 });
  }

  openQuickPostDialog(): void {
    const dialogRef = this.dialog.open(QuickPostDialogComponent, {
      width: '500px',
      disableClose: true,
      panelClass: 'marketing-dialog-panel'
    });
    dialogRef.afterClosed().subscribe(() => this.loadQuickPosts());
  }

  loadQuickPosts(): void {
    this.marketingService.getQuickPosts(20).subscribe({
      next: (posts) => {
        this.quickPosts = posts;
        this.applyFilter(); // Apply current filters to quick posts
      },
      error: (err) => console.error('Failed to load quick posts', err)
    });
  }

  deleteQuickPost(post: CampaignEvent): void {
    if (confirm('Delete this quick post?')) {
      this.marketingService.deleteEvent(post.id).subscribe({
        next: () => {
          this.quickPosts = this.quickPosts.filter(p => p.id !== post.id);
          this.applyFilter();
          this.snackBar.open('Quick post deleted', 'Close', { duration: 2000 });
        },
        error: (err) => {
          console.error('Failed to delete quick post', err);
          this.snackBar.open('Failed to delete', 'Close', { duration: 3000 });
        }
      });
    }
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

  openQuickPostDetail(post: CampaignEvent): void {
    const dialogRef = this.dialog.open(QuickPostDetailDialogComponent, {
      data: { post },
      width: '600px',
      maxWidth: '95vw',
      panelClass: 'marketing-dialog-panel'
    });
    dialogRef.afterClosed().subscribe(() => this.loadQuickPosts());
  }

  deleteCampaign(campaign: CampaignSummary): void {
    if (confirm(`Delete campaign "${campaign.name}"?`)) {
      this.marketingService.deleteCampaign(campaign.id).subscribe({
        next: () => {
          this.campaigns = this.campaigns.filter(c => c.id !== campaign.id);
          this.applyFilter();
          this.snackBar.open('Campaign deleted', 'Close', { duration: 2000 });
        },
        error: (err) => {
          console.error('Failed to delete campaign', err);
          this.snackBar.open('Failed to delete campaign', 'Close', { duration: 3000 });
        }
      });
    }
  }
}

