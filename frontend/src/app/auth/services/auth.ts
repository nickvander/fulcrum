import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { tap } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly JWT_TOKEN = 'FULCRUM_JWT_TOKEN';
  private isAuthenticatedSubject = new BehaviorSubject<boolean>(this.hasToken());

  public isAuthenticated$: Observable<boolean> = this.isAuthenticatedSubject.asObservable();

  constructor(private http: HttpClient, private router: Router) {}

  login(credentials: {email: string, password: string}): Observable<any> {
    // TODO: Replace with actual API call
    // For now, simulate a successful login and create a dummy token
    return of({ token: 'dummy-jwt-token' }).pipe(
      tap(response => {
        this.setToken(response.token);
        this.isAuthenticatedSubject.next(true);
        this.router.navigate(['/dashboard']);
      })
    );
  }

  logout(): void {
    this.removeToken();
    this.isAuthenticatedSubject.next(false);
    this.router.navigate(['/login']);
  }

  public getToken(): string | null {
    return localStorage.getItem(this.JWT_TOKEN);
  }

  public isLoggedIn(): boolean {
    return this.hasToken();
  }

  private hasToken(): boolean {
    return !!localStorage.getItem(this.JWT_TOKEN);
  }

  private setToken(token: string): void {
    localStorage.setItem(this.JWT_TOKEN, token);
  }

  private removeToken(): void {
    localStorage.removeItem(this.JWT_TOKEN);
  }
}
