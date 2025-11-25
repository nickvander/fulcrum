import { Observable, of } from 'rxjs';
import { UserListParams, CreateUserRequest } from './user.service';
import { User } from '../models/user.model';

export class UserServiceMock {
  static mockUser: User = {
    id: 1,
    email: 'test@example.com',
    employee_id: 'EMP123456',
    first_name: 'Test',
    last_name: 'User',
    user_type: 'employee',
    is_active: true,
    is_superuser: false,
    avatar: 'https://example.com/avatar.jpg',
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z'
  };

  static mockUsers: User[] = [
    {
      id: 1,
      email: 'admin@test.com',
      employee_id: 'ADM123456',
      first_name: 'Admin',
      last_name: 'User',
      user_type: 'admin',
      is_active: true,
      is_superuser: true,
      avatar: 'https://example.com/admin-avatar.jpg',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z'
    },
    {
      id: 2,
      email: 'employee@test.com',
      employee_id: 'EMP789012',
      first_name: 'Employee',
      last_name: 'User',
      user_type: 'employee',
      is_active: true,
      is_superuser: false,
      avatar: null,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z'
    }
  ];

  getUsers(params?: UserListParams): Observable<User[]> {
    if (params && params.user_type) {
      return of(UserServiceMock.mockUsers.filter(user => user.user_type === params.user_type));
    }
    return of(UserServiceMock.mockUsers);
  }

  getUser(id: number): Observable<User> {
    const user = UserServiceMock.mockUsers.find(u => u.id === id) || UserServiceMock.mockUser;
    return of(user);
  }

  updateUser(id: number, user: Partial<User>): Observable<User> {
    const existingUser = UserServiceMock.mockUsers.find(u => u.id === id);
    if (existingUser) {
      Object.assign(existingUser, user);
      return of(existingUser);
    }
    return of({ ...UserServiceMock.mockUser, ...user, id });
  }

  createUser(user: CreateUserRequest): Observable<User> {
    const newUser = {
      ...UserServiceMock.mockUser,
      id: UserServiceMock.mockUsers.length + 1,
      ...user,
      user_type: user.user_type || 'employee'
    };
    UserServiceMock.mockUsers.push(newUser);
    return of(newUser);
  }

  deleteUser(id: number): Observable<any> {
    const userIndex = UserServiceMock.mockUsers.findIndex(u => u.id === id);
    if (userIndex !== -1) {
      UserServiceMock.mockUsers.splice(userIndex, 1);
    }
    return of({ message: 'User deactivated successfully' });
  }

  deleteUserPermanent(id: number): Observable<any> {
    const userIndex = UserServiceMock.mockUsers.findIndex(u => u.id === id);
    if (userIndex !== -1) {
      UserServiceMock.mockUsers.splice(userIndex, 1);
    }
    return of({ message: 'User permanently deleted successfully' });
  }

  getProfile(): Observable<User> {
    return of(UserServiceMock.mockUser);
  }

  updateProfile(user: Partial<User>): Observable<User> {
    Object.assign(UserServiceMock.mockUser, user);
    return of(UserServiceMock.mockUser);
  }

  requestPasswordReset(email: string): Observable<any> {
    return of({ message: 'If the email exists, a reset link has been sent' });
  }

  resetPassword(token: string, newPassword: string): Observable<any> {
    return of({ message: 'Password reset successful' });
  }

  adminResetPassword(userId: number): Observable<{ message: string, new_password?: string }> {
    return of({
      message: 'Password reset successfully. New password has been generated and should be communicated to the user securely.',
      new_password: 'GeneratedPassword123!'
    });
  }
}