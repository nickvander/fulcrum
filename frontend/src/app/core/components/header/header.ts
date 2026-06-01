import { Component, EventEmitter, Input, OnDestroy, OnInit, Output } from '@angular/core';
import { Subscription } from 'rxjs';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSidenav } from '@angular/material/sidenav';
import { TranslocoModule } from '@ngneat/transloco';
import { AuthService } from '../../services/auth.service';
import { BrandPulseService } from '../../services/brand-pulse.service';

@Component({
  selector: 'app-header',
  templateUrl: './header.html',
  styleUrls: ['./header.scss'],
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatDividerModule,
    MatTooltipModule,
    TranslocoModule
  ]
})
export class Header implements OnInit, OnDestroy {
  user$;
  @Input() drawer!: MatSidenav;
  /** True on desktop: the menu button collapses the rail instead of opening a drawer. */
  @Input() desktop = false;
  /** Emitted (desktop only) to toggle the persistent rail collapse. */
  @Output() collapseToggle = new EventEmitter<void>();

  /** True for the brief sync-pulse animation window on the brand wedge. */
  syncing = false;

  /** Animation duration (ms) — must match the brand-wedge-pulse keyframe. */
  readonly SYNC_PULSE_MS = 760;

  private pulseSub?: Subscription;
  private syncTimer?: ReturnType<typeof setTimeout>;

  constructor(
    private authService: AuthService,
    private brandPulse: BrandPulseService,
  ) {
    this.user$ = this.authService.getCurrentUserObservable();
  }

  ngOnInit(): void {
    this.pulseSub = this.brandPulse.pulse$.subscribe(() => this.playSyncPulse());
  }

  ngOnDestroy(): void {
    this.pulseSub?.unsubscribe();
    if (this.syncTimer) {
      clearTimeout(this.syncTimer);
    }
  }

  /**
   * Toggle the `syncing` class for the animation window, then clear it so a
   * later pulse can re-trigger the keyframe. Restart cleanly if a pulse
   * arrives mid-animation.
   */
  private playSyncPulse(): void {
    if (this.syncTimer) {
      clearTimeout(this.syncTimer);
    }
    this.syncing = true;
    this.syncTimer = setTimeout(() => {
      this.syncing = false;
      this.syncTimer = undefined;
    }, this.SYNC_PULSE_MS);
  }

  onMenu(): void {
    if (this.desktop) {
      this.collapseToggle.emit();
    } else {
      this.drawer.toggle();
    }
  }

  logout(): void {
    this.authService.logout();
  }

  getUserInitials(user: any): string {
    if (!user) return '';
    if (user.first_name && user.last_name) {
      return (user.first_name[0] + user.last_name[0]).toUpperCase();
    }
    return user.email?.slice(0, 2).toUpperCase() || 'U';
  }
}
