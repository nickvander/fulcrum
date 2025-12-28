import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

export const LoginGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isLoggedIn()) {
    // User is already logged in, redirect to dashboard page
    router.navigate(['/dashboard']);
    return false;
  } else {
    // User is not logged in, allow access to login page
    return true;
  }
};