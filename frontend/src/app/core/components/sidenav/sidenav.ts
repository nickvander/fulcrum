import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { AuthService } from '../../services/auth.service';
import { User } from '../../../shared/models/user.model';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';

@Component({
  selector: 'app-sidenav',
  templateUrl: './sidenav.html',
  styleUrls: ['./sidenav.scss'],
  standalone: true,
  imports: [CommonModule, RouterModule, MatListModule, MatIconModule, MatExpansionModule, MatButtonModule, MatTooltipModule],
})
export class Sidenav implements OnInit {
  isAdmin$!: Observable<boolean>;
  purchasingExpanded = true;
  currentUser$!: Observable<User | null>;

  constructor(private authService: AuthService) { }

  ngOnInit(): void {
    this.isAdmin$ = this.authService.isAdmin();
    this.currentUser$ = this.authService.getCurrentUserObservable();
  }

  logout(): void {
    this.authService.logout();
  }

  getUserDisplayName(user: User | null): string {
    if (!user) return 'User';
    if (user.first_name && user.last_name) return `${user.first_name} ${user.last_name}`;
    if (user.first_name) return user.first_name;
    if (user.last_name) return user.last_name;
    return user.email?.split('@')[0] || 'User';
  }

  getUserInitials(user: User | null): string {
    if (!user) return 'U';
    const name = this.getUserDisplayName(user);
    const parts = name.split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  }

  getUserRole(user: User | null): string {
    if (!user) return '';
    switch (user.user_type) {
      case 'admin': return 'Admin';
      case 'employee': return 'Employee';
      case 'customer': return 'Customer';
      default: return user.user_type || 'User';
    }
  }
}
