import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Observable } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-sidenav',
  templateUrl: './sidenav.html',
  styleUrls: ['./sidenav.scss'],
  standalone: true,
  imports: [CommonModule, MatListModule, MatIconModule],
})
export class Sidenav implements OnInit {
  isSuperuser$!: Observable<boolean>;

  constructor(private authService: AuthService) {}

  ngOnInit(): void {
    this.isSuperuser$ = this.authService.isSuperuser();
  }
}
