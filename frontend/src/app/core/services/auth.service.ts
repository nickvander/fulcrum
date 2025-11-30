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
    const hasToken = !!localStorage.getItem(this.JWT_TOKEN);
    console.log('AuthService: Checking if token exists in localStorage', hasToken);
    return hasToken;
  }

  private getCurrentUser(): User | null {
    const userData = localStorage.getItem(this.USER_DATA);
    console.log('AuthService: Getting user data from localStorage', userData);
    if (userData) {
      try {
        const parsed = JSON.parse(userData);
        console.log('AuthService: Parsed user data', parsed);
        return parsed;
      } catch (error) {
        console.error('AuthService: Error parsing user data from localStorage', error);
        return null;
      }
    }
    console.log('AuthService: No user data found in localStorage');
    return null;
  }

  isLoggedIn(): Observable<boolean> {
    return this.loggedIn.asObservable();
  }

  getToken(): string | null {
    const token = localStorage.getItem(this.JWT_TOKEN);
    console.log('AuthService: Getting token from localStorage', token ? 'Token exists' : 'No token');
    return token;
  }

  saveToken(token: string): void {
    localStorage.setItem(this.JWT_TOKEN, token);
    this.loggedIn.next(true);
  }

  saveCurrentUser(user: User): void {
    console.log('AuthService: Saving current user to localStorage', user);
    localStorage.setItem(this.USER_DATA, JSON.stringify(user));
    this.currentUser.next(user);
  }

  getCurrentUserObservable(): Observable<User | null> {
    return this.currentUser.asObservable();
  }

  getCurrentUserFromStorage(): User | null {
    return this.getCurrentUser();
  }

  login(credentials: { username: string, password: string }): Observable<User> {
    console.log('AuthService: Attempting login for', credentials.username);
    const formData = new URLSearchParams();
    formData.set('username', credentials.username);
    formData.set('password', credentials.password);

    return this.http.post<any>('/api/v1/users/login/access-token', formData.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    }).pipe(
      tap((res: any) => {
        console.log('AuthService: Received token response', res);
        this.saveToken(res.access_token);
      }),
      // After logging in, fetch the user profile to get user details
      switchMap(() => this.fetchUserProfile()),
      // Handle case where fetchUserProfile returns null
      map(user => {
        console.log('AuthService: Received user profile', user);
        if (!user) {
          console.error('AuthService: Failed to fetch user profile after login');
          throw new Error('Failed to fetch user profile after login');
        }
        return user;
      }),
      catchError(error => {
        console.error('AuthService: Error during login process', error);
        throw error;
      })
    );
  }

  private fetchUserProfile(): Observable<User> {
    const token = this.getToken();
    if (!token) {
      console.error('AuthService: No token available for fetching user profile');
      return throwError(() => new Error('No token available'));
    }

    console.log('AuthService: Fetching user profile with token');
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });

    return this.http.get<User>('/api/v1/users/profile', { headers }).pipe(
      tap(user => {
        console.log('AuthService: Successfully fetched user profile', user);
        this.saveCurrentUser(user);

        // Check if user needs to change password
        if (user.force_password_change) {
          console.log('AuthService: User must change password, redirecting...');
          this.router.navigate(['/users/force-password-change']);
        }
      }),
      catchError(error => {
        console.error('AuthService: Error fetching user profile', error);
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
      console.log('AuthService: Returning cached isAdmin result', user.user_type === 'admin');
      return of(user.user_type === 'admin');
    }

    console.log('AuthService: No cached user data, fetching from API');
    // If we don't have user data in storage, fetch it
    return this.fetchUserProfile().pipe(
      map(user => {
        const result = user ? user.user_type === 'admin' : false;
        console.log('AuthService: Returning isAdmin result from API', result);
        return result;
      }),
      catchError((error) => {
        console.error('AuthService: Error in isAdmin()', error);
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
