import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, of, BehaviorSubject, throwError } from 'rxjs';
import { tap, map, catchError, switchMap } from 'rxjs/operators';
import { User } from '../../shared/models/user.model';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly JWT_TOKEN = 'FULCRUM_JWT_TOKEN';
  private readonly USER_DATA = 'FULCRUM_USER_DATA';
  private loggedIn = new BehaviorSubject<boolean>(this.hasToken());
  private currentUser = new BehaviorSubject<User | null>(this.getCurrentUser());

  constructor(private http: HttpClient, private router: Router) { }

  private hasToken(): boolean {
    return !!localStorage.getItem(this.JWT_TOKEN);
  }

  private getCurrentUser(): User | null {
    const userData = localStorage.getItem(this.USER_DATA);
    if (userData) {
      try {
        return JSON.parse(userData);
      } catch (error) {
        return null;
      }
    }
    return null;
  }

  isLoggedIn(): boolean {
    return this.hasToken();
  }

  isLoggedIn$(): Observable<boolean> {
    return this.loggedIn.asObservable();
  }

  // Legacy name for backward compatibility during transition
  isLoggedInObservable(): Observable<boolean> {
    return this.isLoggedIn$();
  }

  getToken(): string | null {
    const token = localStorage.getItem(this.JWT_TOKEN);
    return token;
  }

  saveToken(token: string): void {
    localStorage.setItem(this.JWT_TOKEN, token);
    this.loggedIn.next(true);
  }

  saveCurrentUser(user: User): void {
    localStorage.setItem(this.USER_DATA, JSON.stringify(user));
    this.currentUser.next(user);
  }

  getCurrentUserObservable(): Observable<User | null> {
    return this.currentUser.asObservable();
  }

  getCurrentUserFromStorage(): User | null {
    return this.getCurrentUser();
  }

  login(credentials: { email?: string, username?: string, password: string }): Observable<User> {
    const username = credentials.username || credentials.email || '';
    const formData = new URLSearchParams();
    formData.set('username', username);
    formData.set('password', credentials.password);

    return this.http.post<any>('/api/v1/users/login/access-token', formData.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    }).pipe(
      tap((res: any) => {
        this.saveToken(res.access_token);
      }),
      // After logging in, fetch the user profile to get user details
      switchMap(() => this.fetchUserProfile()),
      map(user => {
        if (!user) {
          throw new Error('Failed to fetch user profile after login');
        }
        return user;
      })
    );
  }

  requestPasswordReset(email: string): Observable<any> {
    return this.http.post<any>('/api/v1/users/password-reset-request', { email });
  }

  resetPassword(token: string, newPassword: string): Observable<any> {
    return this.http.post<any>('/api/v1/users/password-reset', { token, new_password: newPassword });
  }

  private fetchUserProfile(): Observable<User> {
    const token = this.getToken();
    if (!token) {
      return throwError(() => new Error('No token available'));
    }

    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });

    return this.http.get<User>('/api/v1/users/profile', { headers }).pipe(
      tap(user => {
        this.saveCurrentUser(user);

        // Check if user needs to change password
        if (user.force_password_change) {
          this.router.navigate(['/users/force-password-change']);
        }
      }),
      catchError(error => {
        throw error;
      })
    );
  }

  logout(): void {
    localStorage.removeItem(this.JWT_TOKEN);
    localStorage.removeItem(this.USER_DATA);
    this.loggedIn.next(false);
    this.currentUser.next(null);
    this.router.navigate(['/login']);
  }

  isSuperuser(): Observable<boolean> {
    const user = this.getCurrentUser();
    if (user) {
      return of(user.is_superuser);
    }

    // If we don't have user data in storage, fetch it
    return this.fetchUserProfile().pipe(
      map(user => user ? user.is_superuser : false),
      catchError(() => of(false))
    );
  }

  isAdmin(): Observable<boolean> {
    const user = this.getCurrentUser();
    if (user) {
      return of(user.user_type === 'admin');
    }

    // If we don't have user data in storage, fetch it
    return this.fetchUserProfile().pipe(
      map(user => {
        return user ? user.user_type === 'admin' : false;
      }),
      catchError((error) => {
        return of(false);
      })
    );
  }

  isEmployee(): Observable<boolean> {
    const user = this.getCurrentUser();
    if (user) {
      return of(user.user_type === 'admin' || user.user_type === 'employee');
    }

    // If we don't have user data in storage, fetch it
    return this.fetchUserProfile().pipe(
      map(user => user ? (user.user_type === 'admin' || user.user_type === 'employee') : false),
      catchError(() => of(false))
    );
  }

  isCustomer(): Observable<boolean> {
    const user = this.getCurrentUser();
    if (user) {
      return of(user.user_type === 'customer');
    }

    // If we don't have user data in storage, fetch it
    return this.fetchUserProfile().pipe(
      map(user => user ? user.user_type === 'customer' : false),
      catchError(() => of(false))
    );
  }
}
