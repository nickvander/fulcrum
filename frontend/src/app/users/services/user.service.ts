import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { User } from '../../shared/models/user.model';
import { environment } from '../../../environments/environment';

export interface UserListParams {
  skip?: number;
  limit?: number;
  user_type?: string;
  is_active?: boolean;
  search?: string;
}

export interface CreateUserRequest {
  email: string;
  first_name?: string;
  last_name?: string;
  user_type?: 'admin' | 'employee' | 'customer';
  is_active?: boolean;
  is_superuser?: boolean;
  avatar?: string;
  password: string;
}

@Injectable()
export class UserService {
  private apiUrl = `${environment.apiUrl}/users`;

  constructor(private http: HttpClient) { }

  getUsers(params?: UserListParams): Observable<User[]> {
    let httpParams = new HttpParams();

    if (params) {
      if (params.skip !== undefined) httpParams = httpParams.set('skip', params.skip.toString());
      if (params.limit !== undefined) httpParams = httpParams.set('limit', params.limit.toString());
      if (params.user_type) httpParams = httpParams.set('user_type', params.user_type);
      if (params.is_active !== undefined) httpParams = httpParams.set('is_active', params.is_active.toString());
      if (params.search) httpParams = httpParams.set('search', params.search);
    }

    return this.http.get<User[]>(`${this.apiUrl}/`, { params: httpParams });
  }

  getUser(id: number): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/${id}`);
  }

  updateUser(id: number, user: Partial<User>): Observable<User> {
    return this.http.put<User>(`${this.apiUrl}/${id}`, user);
  }

  createUser(user: CreateUserRequest): Observable<User> {
    return this.http.post<User>(`${this.apiUrl}/`, user);
  }

  deleteUser(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${id}`);
  }

  deleteUserPermanent(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${id}/permanent`);
  }

  getProfile(): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/profile`);
  }

  updateProfile(user: Partial<User>): Observable<User> {
    return this.http.put<User>(`${this.apiUrl}/profile`, user);
  }

  // Password reset functionality
  requestPasswordReset(email: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/password-reset-request`, { email });
  }

  resetPassword(token: string, newPassword: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/password-reset`, { token, new_password: newPassword });
  }

  adminResetPassword(userId: number): Observable<{ message: string, new_password?: string }> {
    return this.http.post<{ message: string, new_password?: string }>(`${this.apiUrl}/${userId}/admin-reset-password`, {});
  }

  bulkImportUsers(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post(`${environment.apiUrl}/bulk-users/bulk-import`, formData);
  }

  changePassword(currentPassword: string, newPassword: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/change-password`, { current_password: currentPassword, new_password: newPassword });
  }
}
