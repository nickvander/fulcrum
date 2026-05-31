import { Component, EventEmitter, Input, Output } from '@angular/core';
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
export class Header {
  user$;
  @Input() drawer!: MatSidenav;
  /** True on desktop: the menu button collapses the rail instead of opening a drawer. */
  @Input() desktop = false;
  /** Emitted (desktop only) to toggle the persistent rail collapse. */
  @Output() collapseToggle = new EventEmitter<void>();

  constructor(private authService: AuthService) {
    this.user$ = this.authService.getCurrentUserObservable();
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
