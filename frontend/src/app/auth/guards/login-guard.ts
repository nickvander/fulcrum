import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth';

export const LoginGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isLoggedIn()) {
    // User is already logged in, redirect to products page
    router.navigate(['/products']);
    return false;
  } else {
    // User is not logged in, allow access to login page
    return true;
  }
};