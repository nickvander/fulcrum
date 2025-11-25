import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { UserService } from './user.service';
import { environment } from '../../../environments/environment';

describe('UserService - Comprehensive Tests', () => {
  let service: UserService;
  let httpTestingController: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [UserService]
    });
    
    service = TestBed.inject(UserService);
    httpTestingController = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTestingController.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should fetch users list', () => {
    const mockUsers = [
      { id: 1, email: 'user1@test.com', user_type: 'employee' },
      { id: 2, email: 'user2@test.com', user_type: 'admin' }
    ];

    let result: any;
    service.getUsers().subscribe(users => {
      result = users;
    });

    const req = httpTestingController.expectOne(`${environment.apiUrl}/users`);
    expect(req.request.method).toBe('GET');
    req.flush(mockUsers);

    expect(result.length).toBe(2);
    expect(result[0].email).toBe('user1@test.com');
  });

  it('should fetch users with filters', () => {
    const mockUsers = [{ id: 1, email: 'filtered@test.com', user_type: 'admin' }];
    
    service.getUsers({ user_type: 'admin', is_active: true }).subscribe(users => {
      expect(users.length).toBe(1);
      expect(users[0].user_type).toBe('admin');
    });

    const req = httpTestingController.expectOne(
      `${environment.apiUrl}/users?skip=0&limit=100&user_type=admin&is_active=true`
    );
    expect(req.request.method).toBe('GET');
    req.flush(mockUsers);
  });

  it('should fetch single user', () => {
    const mockUser = { id: 1, email: 'single@test.com', user_type: 'employee' };

    service.getUser(1).subscribe(user => {
      expect(user.id).toBe(1);
      expect(user.email).toBe('single@test.com');
    });

    const req = httpTestingController.expectOne(`${environment.apiUrl}/users/1`);
    expect(req.request.method).toBe('GET');
    req.flush(mockUser);
  });

  it('should create user', () => {
    const newUser = {
      email: 'new@test.com',
      first_name: 'New',
      last_name: 'User',
      user_type: 'employee',
      password: 'TestPass123!'
    };
    
    const returnedUser = { ...newUser, id: 3, is_active: true, is_superuser: false };

    service.createUser(newUser).subscribe(user => {
      expect(user.id).toBe(3);
      expect(user.email).toBe('new@test.com');
    });

    const req = httpTestingController.expectOne(`${environment.apiUrl}/users`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(newUser);
    req.flush(returnedUser);
  });

  it('should update user', () => {
    const updatedData = { first_name: 'Updated', last_name: 'Name' };
    const updatedUser = { id: 1, email: 'test@test.com', ...updatedData, user_type: 'employee' };

    service.updateUser(1, updatedData).subscribe(user => {
      expect(user.first_name).toBe('Updated');
      expect(user.last_name).toBe('Name');
    });

    const req = httpTestingController.expectOne(`${environment.apiUrl}/users/1`);
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual(updatedData);
    req.flush(updatedUser);
  });

  it('should deactivate user', () => {
    service.deleteUser(1).subscribe(response => {
      expect(response).toEqual({ message: 'User deactivated successfully' });
    });

    const req = httpTestingController.expectOne(`${environment.apiUrl}/users/1`);
    expect(req.request.method).toBe('DELETE');
    req.flush({ message: 'User deactivated successfully' });
  });

  it('should permanently delete user', () => {
    service.deleteUserPermanent(1).subscribe(response => {
      expect(response).toEqual({ message: 'User permanently deleted successfully' });
    });

    const req = httpTestingController.expectOne(`${environment.apiUrl}/users/1/permanent`);
    expect(req.request.method).toBe('DELETE');
    req.flush({ message: 'User permanently deleted successfully' });
  });

  it('should get user profile', () => {
    const mockProfile = { id: 1, email: 'profile@test.com', first_name: 'Profile' };

    service.getProfile().subscribe(profile => {
      expect(profile.email).toBe('profile@test.com');
    });

    const req = httpTestingController.expectOne(`${environment.apiUrl}/users/profile`);
    expect(req.request.method).toBe('GET');
    req.flush(mockProfile);
  });

  it('should update user profile', () => {
    const updateData = { first_name: 'Updated', last_name: 'Profile' };
    const updatedProfile = { id: 1, email: 'profile@test.com', ...updateData };

    service.updateProfile(updateData).subscribe(profile => {
      expect(profile.first_name).toBe('Updated');
    });

    const req = httpTestingController.expectOne(`${environment.apiUrl}/users/profile`);
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual(updateData);
    req.flush(updatedProfile);
  });

  it('should request password reset', () => {
    service.requestPasswordReset('test@example.com').subscribe(response => {
      expect(response.message).toContain('reset link has been sent');
    });

    const req = httpTestingController.expectOne(`${environment.apiUrl}/users/password-reset-request`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ email: 'test@example.com' });
    req.flush({ message: 'If the email exists, a reset link has been sent' });
  });

  it('should reset password', () => {
    service.resetPassword('token123', 'NewPass123!').subscribe(response => {
      expect(response.message).toBe('Password reset successful');
    });

    const req = httpTestingController.expectOne(`${environment.apiUrl}/users/password-reset`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ token: 'token123', new_password: 'NewPass123!' });
    req.flush({ message: 'Password reset successful' });
  });

  it('should reset user password by admin', () => {
    service.adminResetPassword(1).subscribe(response => {
      expect(response.message).toContain('Password reset successfully');
      expect(response.new_password).toBeDefined();
    });

    const req = httpTestingController.expectOne(`${environment.apiUrl}/users/1/admin-reset-password`);
    expect(req.request.method).toBe('POST');
    req.flush({
      message: 'Password reset successfully. New password has been generated and should be communicated to the user securely.',
      new_password: 'GeneratedPassword123!'
    });
  });
});