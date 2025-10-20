import { Injectable } from '@angular/core';
import { CanActivate, Router, UrlTree } from '@angular/router';
import { Observable, map, take } from 'rxjs';
import { AuthService } from '../services/auth.service';

@Injectable({
  providedIn: 'root'
})
export class AdminGuard implements CanActivate {
  constructor(private authService: AuthService, private router: Router) {}

  canActivate(): Observable<boolean | UrlTree> {
    return this.authService.isAdmin().pipe(
      take(1),
      map(isAdmin => {
        if (isAdmin) {
          return true;
        } else {
          // Redirect to home or show unauthorized page
          return this.router.createUrlTree(['/']);
        }
      })
    );
  }
}