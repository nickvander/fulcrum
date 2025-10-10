import { Component, OnInit } from '@angular/core';
import { Observable } from 'rxjs';
import { AuthService } from '../../services/auth';

@Component({
  selector: 'app-sidenav',
  templateUrl: './sidenav.html',
  styleUrls: ['./sidenav.scss'],
})
export class Sidenav implements OnInit {
  isSuperuser$!: Observable<boolean>;

  constructor(private authService: AuthService) {}

  ngOnInit(): void {
    this.isSuperuser$ = this.authService.isSuperuser();
  }
}
