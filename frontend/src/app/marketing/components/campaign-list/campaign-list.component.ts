import { Component, OnInit, ViewChild, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatTableModule, MatTableDataSource } from '@angular/material/table'; // Added DataSource
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatCardModule } from '@angular/material/card';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator'; // Added Paginator
import { MatSort, MatSortModule } from '@angular/material/sort';

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
    MatPaginatorModule,
    MatSortModule,
    DateRangePresetsComponent,
    StatusFilterComponent
  ],
  templateUrl: './campaign-list.component.html',
  styleUrls: ['./campaign-list.component.scss']
})
export class CampaignListComponent implements OnInit, AfterViewInit {
  campaigns: CampaignSummary[] = [];
  // Use MatTableDataSource for pagination support
  filteredCampaigns = new MatTableDataSource<CampaignSummary>([]);
  quickPosts: CampaignEvent[] = [];
  filteredQuickPosts: CampaignEvent[] = [];
  statusFilter: string = 'all';
  dateRange: DateRange | null = null;
  loading = true;
  displayedColumns = ['name', 'status', 'dates', 'events', 'products', 'actions'];

  @ViewChild('campaignPaginator') campaignPaginator!: MatPaginator;
  @ViewChild(MatSort) set matSort(sort: MatSort) {
    this.filteredCampaigns.sort = sort;
  }
  @ViewChild('quickPostPaginator') quickPostPaginator!: MatPaginator;

  statusOptions: StatusFilterOption[] = [
    { value: 'all', label: 'All' },
    { value: 'draft', label: 'Draft', icon: 'edit_note' },
    { value: 'scheduled', label: 'Scheduled', icon: 'schedule' },
    { value: 'active', label: 'Active', icon: 'play_circle' },
    { value: 'completed', label: 'Done', icon: 'check_circle' }
  ];

  // Quick Post Pagination
  quickPostPageSize = 5;
  quickPostPageIndex = 0;
  visibleQuickPosts: CampaignEvent[] = [];

  constructor(
    private marketingService: MarketingService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) { }

  ngOnInit(): void {
    this.loadCampaigns();
    this.loadQuickPosts();
  }

  ngAfterViewInit() {
    this.filteredCampaigns.paginator = this.campaignPaginator;
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

    this.filteredCampaigns.data = filtered;

    // Re-assign paginator if data changes heavily (though data binding usually handles it)
    if (this.campaignPaginator) {
      this.filteredCampaigns.paginator = this.campaignPaginator;
    }

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
    this.updateVisibleQuickPosts();

    // Reset to first page when filters change
    if (this.quickPostPaginator) {
      this.quickPostPaginator.firstPage();
    }
  }

  updateVisibleQuickPosts() {
    const start = this.quickPostPageIndex * this.quickPostPageSize;
    const end = start + this.quickPostPageSize;
    this.visibleQuickPosts = this.filteredQuickPosts.slice(start, end);
  }

  onQuickPostPageChange(event: any) {
    this.quickPostPageIndex = event.pageIndex;
    this.quickPostPageSize = event.pageSize;
    this.updateVisibleQuickPosts();
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

