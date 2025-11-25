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
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatTableModule } from '@angular/material/table';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { UserList } from './user-list';
import { UserService } from '../../services/user.service';
import { UserServiceMock } from '../../services/user.service.mock';
import { User } from '../../models/user.model';
import { AuthService } from '../../../core/services/auth.service';
import { Router } from '@angular/router';

describe('UserList - UX Tests', () => {
  let component: UserList;
  let fixture: ComponentFixture<UserList>;
  let userService: UserService;
  let authService: jasmine.SpyObj<AuthService>;
  let router: Router;

  beforeEach(async () => {
    const authServiceSpy = jasmine.createSpyObj('AuthService', ['isAdmin']);
    authServiceSpy.isAdmin.and.returnValue(of(true)); // Mock admin access

    await TestBed.configureTestingModule({
      imports: [
        UserList,
        HttpClientTestingModule,
        ReactiveFormsModule,
        RouterTestingModule.withRoutes([]),
        MatSnackBarModule,
        MatDialogModule,
        MatFormFieldModule,
        MatInputModule,
        MatSelectModule,
        MatButtonModule,
        MatSlideToggleModule,
        MatIconModule,
        MatTooltipModule,
        MatPaginatorModule,
        MatSortModule,
        MatTableModule,
        MatProgressBarModule,
        BrowserAnimationsModule
      ],
      providers: [
        { provide: UserService, useClass: UserServiceMock },
        { provide: AuthService, useValue: authServiceSpy }
      ]
    })
    .compileComponents();

    userService = TestBed.inject(UserService);
    authService = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
    router = TestBed.inject(Router);
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(UserList);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should show loading indicator when loading users', () => {
    // Set loading state
    component.isLoading = true;
    fixture.detectChanges();
    
    const progressBar = fixture.nativeElement.querySelector('mat-progress-bar');
    expect(progressBar).toBeTruthy();
    
    // Check that table has reduced opacity during loading
    const table = fixture.nativeElement.querySelector('mat-table');
    expect(table.style.opacity).toBe('0.5');
  });

  it('should hide loading indicator when not loading', () => {
    // Set not loading state
    component.isLoading = false;
    fixture.detectChanges();
    
    // Loading indicator should be in the DOM but not visible since it's conditional
    component.isLoading = true;
    fixture.detectChanges();
    
    component.isLoading = false;
    fixture.detectChanges();
    
    const progressBar = fixture.nativeElement.querySelector('mat-progress-bar');
    // When isLoading is false, the progress bar should not be added to the DOM
    expect(progressBar).toBeFalsy();
  });

  it('should apply filters correctly', () => {
    // Set up spy
    spyOn(userService, 'getUsers').and.returnValue(of([]));
    
    component.user_type_filter = 'admin';
    component.is_active_filter = 'true';
    component.search_filter = 'test';
    
    component.onFilterChange();
    
    expect(userService.getUsers).toHaveBeenCalledWith({
      user_type: 'admin',
      is_active: true,
      search: 'test'
    });
  });

  it('should clear filters properly', () => {
    component.user_type_filter = 'admin';
    component.is_active_filter = 'true';
    component.search_filter = 'test';
    
    component.clearFilters();
    
    expect(component.user_type_filter).toBe('');
    expect(component.is_active_filter).toBe('');
    expect(component.search_filter).toBe('');
  });

  it('should handle tooltips for user information', () => {
    // The component should render tooltips for avatar and status columns
    const mockUsers: User[] = [
      {
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
      }
    ];
    
    spyOn(userService, 'getUsers').and.returnValue(of(mockUsers));
    component.loadUsers();
    fixture.detectChanges();
    
    // Check that the table has cells with matTooltip directive
    // This is more of a template check
    const avatarCells = fixture.nativeElement.querySelectorAll('.mat-column-avatar');
    expect(avatarCells.length).toBeGreaterThan(0);
  });

  it('should navigate to audit logs page when button is clicked', () => {
    spyOn(router, 'navigate');
    component.viewAuditLogs();
    expect(router.navigate).toHaveBeenCalledWith(['/users/audit-logs']);
  });

  it('should open user creation modal when button is clicked', () => {
    const dialogSpy = spyOn(component['dialog'], 'open').and.returnValue({
      afterClosed: () => of({ id: 1, email: 'newuser@test.com' })
    } as any);
    
    component.addNewUser();
    
    expect(dialogSpy).toHaveBeenCalled();
    expect(dialogSpy).toHaveBeenCalledWith(
      jasmine.any(Function), // UserCreateModal class
      jasmine.objectContaining({ width: '500px' })
    );
  });

  it('should refresh user list after adding a new user', () => {
    spyOn(component, 'loadUsers');
    const dialogSpy = spyOn(component['dialog'], 'open').and.returnValue({
      afterClosed: () => of({ id: 1, email: 'newuser@test.com' })
    } as any);
    
    component.addNewUser();
    
    // The loadUsers method should be called after the modal closes with a result
    expect(component.loadUsers).toHaveBeenCalled();
  });

  it('should handle error when loading users', () => {
    spyOn(userService, 'getUsers').and.returnValue(throwError({ error: 'Network error' }));
    spyOn(console, 'error');
    
    component.loadUsers();
    
    expect(component.isLoading).toBe(false);
    expect(console.error).toHaveBeenCalledWith('Error loading users:', jasmine.any(Object));
  });

  it('should have responsive design elements', () => {
    // Check that header actions container exists
    const headerActions = fixture.nativeElement.querySelector('.header-actions');
    expect(headerActions).toBeTruthy();
  });
});