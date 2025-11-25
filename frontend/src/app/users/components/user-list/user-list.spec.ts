import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { RouterTestingModule } from '@angular/router/testing';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialogModule, MatDialog, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';

import { UserList } from './user-list';
import { UserService } from '../../services/user.service';
import { UserServiceMock } from '../../services/user.service.mock';
import { User } from '../../models/user.model';
import { AuthService } from '../../../core/services/auth.service';

describe('UserList', () => {
  let component: UserList;
  let fixture: ComponentFixture<UserList>;
  let userService: UserService;
  let authService: jasmine.SpyObj<AuthService>;
  let dialogSpy: jasmine.SpyObj<MatDialog>;

  beforeEach(async () => {
    const authServiceSpy = jasmine.createSpyObj('AuthService', ['isAdmin']);
    const matDialogSpy = jasmine.createSpyObj('MatDialog', ['open']);

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
        NoopAnimationsModule
      ],
      providers: [
        { provide: UserService, useClass: UserServiceMock },
        { provide: AuthService, useValue: authServiceSpy },
        { provide: MatDialog, useValue: matDialogSpy }
      ]
    })
      .compileComponents();

    userService = TestBed.inject(UserService);
    authService = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
    dialogSpy = TestBed.inject(MatDialog) as jasmine.SpyObj<MatDialog>;
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(UserList);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load users on initialization', () => {
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

    spyOn(userService, 'getUsers').and.returnValue(of(mockUsers));

    component.loadUsers();

    expect(userService.getUsers).toHaveBeenCalled();
    expect(component.dataSource.data.length).toBe(2);
  });

  it('should apply filters correctly', () => {
    spyOn(userService, 'getUsers').and.returnValue(of([]));

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
    spyOn(userService, 'deleteUser').and.returnValue(of({ message: 'User deactivated' }));

    // Mock dialog ref to return true (confirmed)
    const dialogRefSpyObj = jasmine.createSpyObj({ afterClosed: of(true), close: null });
    dialogSpy.open.and.returnValue(dialogRefSpyObj);

    component.deactivateUser(1);

    expect(dialogSpy.open).toHaveBeenCalled();
    expect(userService.deleteUser).toHaveBeenCalledWith(1);
    expect(component.loadUsers).toHaveBeenCalled();
  });

  it('should permanently delete user', () => {
    spyOn(component, 'loadUsers');
    spyOn(userService, 'deleteUserPermanent').and.returnValue(of({ message: 'User deleted' }));

    // Mock dialog ref to return true (confirmed)
    const dialogRefSpyObj = jasmine.createSpyObj({ afterClosed: of(true), close: null });
    dialogSpy.open.and.returnValue(dialogRefSpyObj);

    component.deleteUser(1);

    expect(dialogSpy.open).toHaveBeenCalled();
    expect(userService.deleteUserPermanent).toHaveBeenCalledWith(1);
    expect(component.loadUsers).toHaveBeenCalled();
  });
});