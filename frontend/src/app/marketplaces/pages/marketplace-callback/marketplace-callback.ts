import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-marketplace-callback',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule, MatSnackBarModule],
  template: `
    <div class="callback-container">
      <mat-spinner *ngIf="loading"></mat-spinner>
      <p *ngIf="loading">Connecting to {{ marketplaceName }}...</p>
      <p *ngIf="error" class="error">{{ error }}</p>
    </div>
  `,
  styles: [
    `
      .callback-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 60vh;
        gap: 16px;
      }
      .error {
        color: #f44336;
        font-weight: 500;
      }
    `,
  ],
})
export class MarketplaceCallbackComponent implements OnInit {
  loading = true;
  error = '';
  marketplaceName = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private http: HttpClient,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    const type = this.route.snapshot.paramMap.get('type') || '';
    this.marketplaceName = type === 'amazon' ? 'Amazon' : 'MercadoLibre';

    const code = this.route.snapshot.queryParamMap.get('code');
    if (!code) {
      this.loading = false;
      this.error = 'No authorization code received from marketplace.';
      return;
    }

    // First, get the marketplace ID
    this.http
      .get<any[]>(`${environment.apiUrl}/marketplace/`)
      .subscribe({
        next: (marketplaces) => {
          const mp = marketplaces.find(
            (m) => m.name.toLowerCase().includes(type.toLowerCase())
          );
          if (!mp) {
            this.loading = false;
            this.error = `Marketplace "${type}" not found in Fulcrum.`;
            return;
          }
          this.exchangeCode(mp.id, code);
        },
        error: (err) => {
          this.loading = false;
          this.error = 'Failed to load marketplaces.';
          console.error(err);
        },
      });
  }

  private exchangeCode(marketplaceId: number, code: string): void {
    this.http
      .get<any>(
        `${environment.apiUrl}/marketplace-credentials/${marketplaceId}/callback`,
        { params: { code } }
      )
      .subscribe({
        next: (response) => {
          this.loading = false;
          this.snackBar.open(
            `${this.marketplaceName} connected successfully!`,
            'Close',
            { duration: 5000 }
          );
          this.router.navigate(['/marketplaces']);
        },
        error: (err) => {
          this.loading = false;
          this.error = `Failed to connect: ${err.error?.detail || err.message}`;
          console.error('Token exchange error:', err);
        },
      });
  }
}
