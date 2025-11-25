import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { RouterTestingModule } from '@angular/router/testing';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute } from '@angular/router';
import { of, throwError } from 'rxjs';

import { UserForm } from './user-form';
import { UserService } from '../../services/user.service';
import { UserServiceMock } from '../../services/user.service.mock';
import { AuthService } from '../../../core/services/auth.service';
import { User } from '../../models/user.model';

describe('UserForm - Create Mode', () => {
  let component: UserForm;
  let fixture: ComponentFixture<UserForm>;
  let userService: UserService;
  let authService: jasmine.SpyObj<AuthService>;

  beforeEach(async () => {
    const authServiceSpy = jasmine.createSpyObj('AuthService', ['isAdmin']);
    authServiceSpy.isAdmin.and.returnValue(of(false));

    await TestBed.configureTestingModule({
      imports: [
        UserForm,
        HttpClientTestingModule,
        ReactiveFormsModule,
        RouterTestingModule,
        MatSnackBarModule,
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
        { provide: UserService, useClass: UserServiceMock },
        { provide: AuthService, useValue: authServiceSpy },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              paramMap: {
                get: (key: string) => null // Default to create mode (no id)
              }
            }
          }
        }
      ]
    })
      .compileComponents();

    userService = TestBed.inject(UserService);
    authService = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(UserForm);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize form with correct validators for new user', () => {
    expect(component.form.get('email')?.validator).toBeTruthy();
    expect(component.form.get('password')?.validator).toBeTruthy();
  });

  it('should validate password strength correctly', () => {
    const passwordControl = component.form.get('password');

    // Test weak password
    passwordControl?.setValue('weak');
    expect(component.getPasswordStrength('weak')).toBeLessThanOrEqual(1);

    // Test strong password
    passwordControl?.setValue('StrongPass123!');
    expect(component.getPasswordStrength('StrongPass123!')).toBeGreaterThanOrEqual(3);
  });

  it('should return correct password strength class', () => {
    const passwordControl = component.form.get('password');

    passwordControl?.setValue('weak');
    expect(component.getPasswordStrengthClass()).toBe('password-strength-weak');

    passwordControl?.setValue('MediumPass1!');
    expect(component.getPasswordStrengthClass()).toBe('password-strength-medium');

    passwordControl?.setValue('StrongPass123!');
    expect(component.getPasswordStrengthClass()).toBe('password-strength-strong');
  });

  it('should return correct password strength label', () => {
    const passwordControl = component.form.get('password');

    passwordControl?.setValue('weak');
    expect(component.getPasswordStrengthLabel()).toBe('Weak');

    passwordControl?.setValue('MediumPass1!');
    expect(component.getPasswordStrengthLabel()).toBe('Medium');

    passwordControl?.setValue('StrongPass123!');
    expect(component.getPasswordStrengthLabel()).toBe('Strong');
  });

  it('should submit form for new user', () => {
    const mockUser: User = {
      id: 1,
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      is_active: true,
      is_superuser: false,
      user_type: 'employee',
      employee_id: 'EMP123456',
      avatar: 'https://example.com/avatar.jpg'
    };

    spyOn(userService, 'createUser').and.returnValue(of(mockUser));

    component.form.patchValue({
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      user_type: 'employee',
      password: 'StrongPass123!',
      confirm_password: 'StrongPass123!'
    });

    spyOn(component['router'], 'navigate');

    component.onSubmit();

    expect(userService.createUser).toHaveBeenCalledWith({
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      user_type: 'employee',
      password: 'StrongPass123!',
      avatar: 'https://example.com/avatar.jpg',
      is_active: true,
      is_superuser: false
    });
  });

  it('should handle form submission error', () => {
    spyOn(userService, 'createUser').and.returnValue(throwError({ error: { detail: 'Email already exists' } }));

    component.form.patchValue({
      email: 'existing@example.com',
      first_name: 'Existing',
      last_name: 'User',
      user_type: 'employee',
      password: 'StrongPass123!',
      confirm_password: 'StrongPass123!'
    });

    spyOn(console, 'error');
    component.onSubmit();

    expect(console.error).toHaveBeenCalledWith('Error creating user:', jasmine.any(Object));
  });

  it('should reset form for "Save and Add Another"', fakeAsync(() => {
    spyOn(component['snackBar'], 'open');

    const mockUser: User = {
      id: 1,
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      is_active: true,
      is_superuser: false,
      user_type: 'employee',
      employee_id: 'EMP123456',
      avatar: null
    };

    spyOn(userService, 'createUser').and.returnValue(of(mockUser));

    component.form.patchValue({
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      user_type: 'employee',
      password: 'StrongPass123!',
      confirm_password: 'StrongPass123!'
    });

    component.onSaveAndAddAnother();

    expect(userService.createUser).toHaveBeenCalled();
    // Check that form is reset to default values
    expect(component.form.get('user_type')?.value).toBe('employee');
    expect(component.form.get('is_active')?.value).toBe(true);

    // Handle setTimeout in onSaveAndAddAnother
    tick(100);
  }));
});

describe('UserForm - Edit Mode', () => {
  let component: UserForm;
  let fixture: ComponentFixture<UserForm>;
  let userService: UserService;
  let authService: jasmine.SpyObj<AuthService>;

  beforeEach(async () => {
    const authServiceSpy = jasmine.createSpyObj('AuthService', ['isAdmin']);
    authServiceSpy.isAdmin.and.returnValue(of(false));

    await TestBed.configureTestingModule({
      imports: [
        UserForm,
        HttpClientTestingModule,
        ReactiveFormsModule,
        RouterTestingModule,
        MatSnackBarModule,
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
        { provide: UserService, useClass: UserServiceMock },
        { provide: AuthService, useValue: authServiceSpy },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              paramMap: {
                get: (key: string) => '1' // Mock ID for edit mode
              }
            }
          }
        }
      ]
    })
      .compileComponents();

    userService = TestBed.inject(UserService);
    authService = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(UserForm);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should load user data when in edit mode', () => {
    // Verify edit mode was set
    expect(component.isEdit).toBe(true);
  });
});