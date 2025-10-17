import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, of, BehaviorSubject } from 'rxjs';
import { tap, map } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private loggedIn = new BehaviorSubject<boolean>(this.hasToken());

  constructor(private http: HttpClient, private router: Router) {}

  private hasToken(): boolean {
    return !!localStorage.getItem('access_token');
  }

  isLoggedIn(): Observable<boolean> {
    return this.loggedIn.asObservable();
  }

  getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  saveToken(token: string): void {
    localStorage.setItem('access_token', token);
    this.loggedIn.next(true);
  }

  login(credentials: {username: string, password: string}): Observable<any> {
    const formData = new URLSearchParams();
    formData.set('username', credentials.username);
    formData.set('password', credentials.password);

    return this.http.post('/api/v1/users/login/access-token', formData.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    }).pipe(
      tap((res: any) => this.saveToken(res.access_token))
    );
  }

  logout(): void {
    localStorage.removeItem('access_token');
    this.loggedIn.next(false);
    this.router.navigate(['/login']);
  }

  isSuperuser(): Observable<boolean> {
    // In a real app, you'd decode the JWT and check the user's roles/claims
    return of(true);
  }
}
