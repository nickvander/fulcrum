import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MarketplacesService, Marketplace } from '../../marketplaces';
import { Observable, of } from 'rxjs';

@Component({
  selector: 'app-marketplace-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatDividerModule,
    MatSnackBarModule,
    MatTooltipModule
  ],
  template: `
    <div class="marketplace-container">
      <div class="page-header">
        <div class="header-text">
          <h1>Marketplace Channels</h1>
          <p>Orchestrate your multi-channel sales and inventory synchronization from one central hub.</p>
        </div>
        <button mat-flat-button color="primary" (click)="comingSoon('Add Integration')">
          <mat-icon>add</mat-icon>
          Link New Account
        </button>
      </div>

      <div class="marketplace-grid">
        @for (market of marketplaces$ | async; track market.id) {
          <mat-card class="channel-card">
            <div class="card-glow" [ngClass]="market.name.toLowerCase()"></div>
            <mat-card-header>
              <div mat-card-avatar class="channel-avatar" [ngClass]="market.name.toLowerCase()">
                <mat-icon>{{ market.name.toLowerCase() === 'amazon' ? 'store' : 'language' }}</mat-icon>
              </div>
              <mat-card-title>{{ market.name }}</mat-card-title>
              <mat-card-subtitle>Active Connection • ID: {{ market.id }}</mat-card-subtitle>
            </mat-card-header>
            
            <mat-card-content>
              <div class="status-indicator">
                <span class="status-dot online"></span>
                <span class="status-text">Operational</span>
                <span class="spacer"></span>
                <mat-chip-set>
                  <mat-chip class="sync-chip">Auto-Sync ON</mat-chip>
                </mat-chip-set>
              </div>

              <div class="quick-stats">
                <div class="stat-item">
                  <span class="stat-value">124</span>
                  <span class="stat-label">Listings</span>
                </div>
                <div class="stat-item">
                  <span class="stat-value success">122</span>
                  <span class="stat-label">Healthy</span>
                </div>
                <div class="stat-item">
                  <span class="stat-value warning">2</span>
                  <span class="stat-label">Issues</span>
                </div>
              </div>

              <p class="channel-description">
                Last full inventory sweep completed 14 minutes ago. No critical API bottlenecks detected.
              </p>
            </mat-card-content>
            
            <mat-divider></mat-divider>
            
            <mat-card-actions align="end">
              <button mat-button (click)="comingSoon('Configuration')">
                <mat-icon>settings</mat-icon>
                Configure
              </button>
              <button mat-stroked-button color="primary" [routerLink]="['/marketplaces', market.id]">
                <mat-icon>list</mat-icon>
                Manage Listings
              </button>
            </mat-card-actions>
          </mat-card>
        } @empty {
          <div class="empty-state">
            <div class="empty-icon-wrapper">
              <mat-icon>cloud_off</mat-icon>
            </div>
            <h2>No Active Channels</h2>
            <p>Ready to scale? Connect your external marketplaces to synchronize your inventory and orders seamlessly.</p>
            <button mat-flat-button color="primary" (click)="comingSoon('Add Integration')">
              Get Started
            </button>
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .marketplace-container {
      padding: 2rem;
      max-width: 1400px;
      margin: 0 auto;
    }
    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      margin-bottom: 3rem;
      border-bottom: 1px solid rgba(0,0,0,0.05);
      padding-bottom: 1.5rem;
    }
    .header-text h1 {
      font-size: 2.25rem;
      font-weight: 800;
      color: #1e293b;
      margin: 0 0 0.5rem 0;
      letter-spacing: -0.025em;
    }
    .header-text p {
      color: #64748b;
      font-size: 1.1rem;
      margin: 0;
    }
    .marketplace-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
      gap: 2rem;
    }
    .channel-card {
      position: relative;
      overflow: hidden;
      border: none;
      box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      background: white;
      border-radius: 16px;
    }
    .channel-card:hover {
      transform: translateY(-8px);
      box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
    }
    .card-glow {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 4px;
    }
    .card-glow.amazon { background: linear-gradient(90deg, #ff9900, #ffc400); }
    .card-glow.mercadolibre { background: linear-gradient(90deg, #ffe600, #ffcc00); }

    .channel-avatar {
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 12px;
      background: #f8fafc;
      color: #64748b;
    }
    .channel-avatar.amazon { background: #fff7ed; color: #f97316; }
    .channel-avatar.mercadolibre { background: #fefce8; color: #eab308; }

    .status-indicator {
      display: flex;
      align-items: center;
      padding: 1rem 0;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      margin-right: 8px;
    }
    .status-dot.online {
      background-color: #22c55e;
      box-shadow: 0 0 8px #22c55e;
    }
    .status-text {
      font-size: 0.875rem;
      font-weight: 600;
      color: #166534;
    }
    .spacer { flex: 1; }
    .sync-chip {
      font-size: 10px;
      height: 24px;
      background: #f1f5f9;
      color: #475569;
    }

    .quick-stats {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1rem;
      padding: 1rem 0;
      background: #f8fafc;
      border-radius: 12px;
      margin-bottom: 1rem;
    }
    .stat-item {
      display: flex;
      flex-col: column;
      align-items: center;
      text-align: center;
    }
    .stat-value {
      display: block;
      font-size: 1.5rem;
      font-weight: 700;
      color: #1e293b;
    }
    .stat-value.success { color: #166534; }
    .stat-value.warning { color: #d97706; }
    .stat-label {
      font-size: 0.75rem;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .channel-description {
      font-size: 0.875rem;
      color: #64748b;
      line-height: 1.5;
      margin: 0.5rem 0 1rem 0;
    }

    .empty-state {
      grid-column: 1 / -1;
      text-align: center;
      padding: 5rem 2rem;
      background: #f8fafc;
      border-radius: 24px;
      border: 2px dashed #e2e8f0;
    }
    .empty-icon-wrapper {
      width: 80px;
      height: 80px;
      background: white;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 1.5rem auto;
      box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);
    }
    .empty-icon-wrapper mat-icon {
      font-size: 40px;
      width: 40px;
      height: 40px;
      color: #cbd5e1;
    }
    .empty-state h2 {
      font-size: 1.5rem;
      font-weight: 700;
      color: #334155;
      margin-bottom: 0.5rem;
    }
    .empty-state p {
      color: #64748b;
      max-width: 400px;
      margin: 0 auto 2rem auto;
      line-height: 1.6;
    }
  `],
})
export class MarketplaceListComponent implements OnInit {
  marketplaces$: Observable<Marketplace[]> = of([]);

  constructor(
    private marketplaceService: MarketplacesService,
    private snackBar: MatSnackBar
  ) { }

  ngOnInit(): void {
    this.marketplaces$ = this.marketplaceService.getMarketplaces();
  }

  comingSoon(feature: string): void {
    this.snackBar.open(`${feature} functionality is coming soon in the next phase!`, 'Close', {
      duration: 3000,
      horizontalPosition: 'right',
      verticalPosition: 'top'
    });
  }
}
