import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../core/services/auth.service';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-qr-redirect',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule],
  template: `
    <div class="redirect-container">
      <mat-spinner diameter="40"></mat-spinner>
      <p>Redirecting...</p>
    </div>
  `,
  styles: [`
    .redirect-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100vh;
      gap: 16px;
      color: var(--text-secondary);
    }
  `]
})
export class QrRedirectComponent implements OnInit {

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private authService: AuthService
  ) { }

  ngOnInit(): void {
    const productId = this.route.snapshot.paramMap.get('id');

    if (!productId) {
      // Invalid QR code, go to home
      this.router.navigate(['/']);
      return;
    }

    if (this.authService.isLoggedIn()) {
      // Logged in user -> Internal Management
      this.router.navigate(['/products', productId]);
    } else {
      // Guest -> Public Store
      this.router.navigate(['/store/products', productId]);
    }
  }
}
