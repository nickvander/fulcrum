import { ComponentFixture, TestBed } from '@angular/core/testing';
import { UserForm } from './user-form';
import { UserService } from '../../services/user.service';
import { UserServiceMock } from '../../services/user.service.mock';
import { AuthService } from '../../../core/services/auth.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router, ActivatedRoute } from '@angular/router';
import { of, throwError } from 'rxjs';

describe('UserForm', () => {
  describe('Create Mode', () => {
    let component: UserForm;
    let fixture: ComponentFixture<UserForm>;
    let userService: UserService;
    let authService: jasmine.SpyObj<AuthService>;

    beforeEach(async () => {
      const authServiceSpy = jasmine.createSpyObj('AuthService', ['isAdmin']);
      authServiceSpy.isAdmin.and.returnValue(of(false));

      const matSnackBarSpy = jasmine.createSpyObj('MatSnackBar', ['open']);
      const routerSpy = jasmine.createSpyObj('Router', ['navigate']);
      routerSpy.navigate.and.returnValue(Promise.resolve(true));

      await TestBed.configureTestingModule({
        imports: [UserForm],
        providers: [
          { provide: UserService, useClass: UserServiceMock },
          { provide: AuthService, useValue: authServiceSpy },
          { provide: MatSnackBar, useValue: matSnackBarSpy },
          { provide: Router, useValue: routerSpy },
          {
            provide: ActivatedRoute,
            useValue: {
              snapshot: {
                paramMap: {
                  get: (key: string) => null
                }
              }
            }
          }
        ]
      }).compileComponents();

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

      passwordControl?.setValue('Test');
      expect(component.getPasswordStrengthClass()).toBe('password-strength-medium');

      passwordControl?.setValue('StrongPass123!');
      expect(component.getPasswordStrengthClass()).toBe('password-strength-strong');
    });

    it('should return correct password strength label', () => {
      const passwordControl = component.form.get('password');

      passwordControl?.setValue('weak');
      expect(component.getPasswordStrengthLabel()).toBe('Weak');

      passwordControl?.setValue('Test');
      expect(component.getPasswordStrengthLabel()).toBe('Medium');

      passwordControl?.setValue('StrongPass123!');
      expect(component.getPasswordStrengthLabel()).toBe('Strong');
    });

    it('should submit form for new user', () => {
      const mockUser: any = {
        id: 1,
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
        user_type: 'employee'
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

      component.onSubmit();

      expect(userService.createUser).toHaveBeenCalled();
    });

    it('should handle form submission error', () => {
      spyOn(userService, 'createUser').and.returnValue(throwError(() => ({ error: { detail: 'Email already exists' } })));
      spyOn(console, 'error');

      component.form.patchValue({
        email: 'existing@example.com',
        first_name: 'Existing',
        last_name: 'User',
        user_type: 'employee',
        password: 'StrongPass123!',
        confirm_password: 'StrongPass123!'
      });

      component.onSubmit();

      expect(console.error).toHaveBeenCalled();
    });
  });

  describe('Edit Mode', () => {
    let component: UserForm;
    let fixture: ComponentFixture<UserForm>;
    let userService: UserService;
    let authService: jasmine.SpyObj<AuthService>;

    beforeEach(async () => {
      const authServiceSpy = jasmine.createSpyObj('AuthService', ['isAdmin']);
      authServiceSpy.isAdmin.and.returnValue(of(false));

      const matSnackBarSpy = jasmine.createSpyObj('MatSnackBar', ['open']);
      const routerSpy = jasmine.createSpyObj('Router', ['navigate']);
      routerSpy.navigate.and.returnValue(Promise.resolve(true));

      await TestBed.configureTestingModule({
        imports: [UserForm],
        providers: [
          { provide: UserService, useClass: UserServiceMock },
          { provide: AuthService, useValue: authServiceSpy },
          { provide: MatSnackBar, useValue: matSnackBarSpy },
          { provide: Router, useValue: routerSpy },
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
      }).compileComponents();

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
});