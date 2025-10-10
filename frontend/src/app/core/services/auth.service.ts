import { Injectable } from '@angular/core';
import { of } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  isSuperuser() {
    // In a real app, you'd decode the JWT and check the user's roles/claims
    return of(true);
  }
}
