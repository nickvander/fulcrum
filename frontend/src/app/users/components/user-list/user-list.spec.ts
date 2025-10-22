import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { RouterTestingModule } from '@angular/router/testing';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { UserList } from './user-list';
import { UserService } from '../../services/user.service';
import { User } from '../../models/user.model';
import { AuthService } from '../../../core/services/auth.service';

describe('UserList', () => {
  let component: UserList;
  let fixture: ComponentFixture<UserList>;
  let userService: jasmine.SpyObj<UserService>;
  let authService: jasmine.SpyObj<AuthService>;

  beforeEach(async () => {
    const userServiceSpy = jasmine.createSpyObj('UserService', ['getUsers', 'deleteUser', 'deleteUserPermanent']);
    const authServiceSpy = jasmine.createSpyObj('AuthService', ['isAdmin']);

    await TestBed.configureTestingModule({
      imports: [
        UserList,
        HttpClientTestingModule,
        ReactiveFormsModule,
        RouterTestingModule,
        MatSnackBarModule,
        MatDialogModule,
        MatFormFieldModule,
        MatInputModule,
        MatSelectModule,
        MatButtonModule,
        MatSlideToggleModule,
        MatIconModule,
        MatTooltipModule,
        BrowserAnimationsModule
      ],
      providers: [
        { provide: UserService, useValue: userServiceSpy },
        { provide: AuthService, useValue: authServiceSpy }
      ]
    })
    .compileComponents();

    userService = TestBed.inject(UserService) as jasmine.SpyObj<UserService>;
    authService = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(UserList);
    component = fixture.componentInstance;
    
    // Mock data for users
    const mockUsers: User[] = [
      {
        id: 1,
        email: 'admin@test.com',
        employee_id: 'ADM123456',
        first_name: 'Admin',
        last_name: 'User',
        user_type: 'admin',
        is_active: true,
        is_superuser: true,
        avatar: 'https://example.com/admin-avatar.jpg'
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
        avatar: null
      }
    ];
    
    userService.getUsers.and.returnValue(of(mockUsers));
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load users on initialization', () => {
    expect(userService.getUsers).toHaveBeenCalled();
    expect(component.dataSource.data.length).toBe(2);
  });

  it('should apply filters correctly', () => {
    component.user_type_filter = 'admin';
    component.onFilterChange();
    
    expect(userService.getUsers).toHaveBeenCalledWith({ user_type: 'admin' });
  });

  it('should clear filters', () => {
    component.user_type_filter = 'admin';
    component.is_active_filter = 'true';
    component.search_filter = 'test';
    
    component.clearFilters();
    
    expect(component.user_type_filter).toBe('');
    expect(component.is_active_filter).toBe('');
    expect(component.search_filter).toBe('');
  });

  it('should deactivate user', () => {
    spyOn(component, 'loadUsers');
    userService.deleteUser.and.returnValue(of({ message: 'User deactivated' }));
    
    component.deactivateUser(1);
    
    expect(userService.deleteUser).toHaveBeenCalledWith(1);
    expect(component.loadUsers).toHaveBeenCalled();
  });

  it('should permanently delete user', () => {
    spyOn(component, 'loadUsers');
    userService.deleteUserPermanent.and.returnValue(of({ message: 'User deleted' }));
    
    component.deleteUser(1);
    
    expect(userService.deleteUserPermanent).toHaveBeenCalledWith(1);
    expect(component.loadUsers).toHaveBeenCalled();
  });
});