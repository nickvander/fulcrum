import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Observable } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatExpansionModule } from '@angular/material/expansion';

@Component({
  selector: 'app-sidenav',
  templateUrl: './sidenav.html',
  styleUrls: ['./sidenav.scss'],
  standalone: true,
  imports: [CommonModule, RouterModule, MatListModule, MatIconModule, MatExpansionModule],
})
export class Sidenav implements OnInit {
  isAdmin$!: Observable<boolean>;
  purchasingExpanded = true;

  constructor(private authService: AuthService) { }

  ngOnInit(): void {
    this.isAdmin$ = this.authService.isAdmin();
  }

  logout(): void {
    this.authService.logout();
  }
}
