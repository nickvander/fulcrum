import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { tap } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import { User } from '../../users/models/user.model';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly JWT_TOKEN = 'FULCRUM_JWT_TOKEN';
  private apiUrl = `${environment.apiUrl}/users`;
  private isAuthenticatedSubject = new BehaviorSubject<boolean>(this.hasToken());

  public isAuthenticated$: Observable<boolean> = this.isAuthenticatedSubject.asObservable();

  constructor(private http: HttpClient, private router: Router) {}

  login(credentials: {email: string, password: string}): Observable<any> {
    const formData = new FormData();
    formData.append('username', credentials.email);
    formData.append('password', credentials.password);

    return this.http.post<any>(`${this.apiUrl}/login/access-token`, formData).pipe(
      tap(response => {
        this.setToken(response.access_token);
        this.isAuthenticatedSubject.next(true);
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
