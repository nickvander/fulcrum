import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { UserCreateModal } from './user-create-modal';
import { UserService } from '../../services/user.service';
import { UserServiceMock } from '../../services/user.service.mock';
import { User } from '../../models/user.model';

describe('UserCreateModal - UX Tests', () => {
  let component: UserCreateModal;
  let fixture: ComponentFixture<UserCreateModal>;
  let userService: UserService;
  let mockDialogRef: jasmine.SpyObj<MatDialogRef<UserCreateModal>>;

  beforeEach(async () => {
    mockDialogRef = jasmine.createSpyObj<MatDialogRef<UserCreateModal>>(
      'MatDialogRef',
      ['close']
    );

    await TestBed.configureTestingModule({
      imports: [
        UserCreateModal,
        HttpClientTestingModule,
        ReactiveFormsModule,
        MatSnackBarModule,
        MatDialogModule,
        MatFormFieldModule,
        MatInputModule,
        MatSelectModule,
        MatButtonModule,
        MatSlideToggleModule,
        BrowserAnimationsModule
      ],
      providers: [
        { provide: UserService, useClass: UserServiceMock },
        { provide: MatDialogRef, useValue: mockDialogRef }
      ]
    })
      .compileComponents();

    userService = TestBed.inject(UserService);
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(UserCreateModal);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize with a valid form', () => {
    expect(component.form.valid).toBeFalsy();

    // Fill required fields
    component.form.patchValue({
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      password: 'ValidPass123!',
      confirm_password: 'ValidPass123!'
    });

    expect(component.form.valid).toBeTruthy();
  });

  it('should show password strength indicator', () => {
    const passwordControl = component.form.get('password');

    // Test weak password
    passwordControl?.setValue('weak');
    expect(component.getPasswordStrength('weak')).toBeLessThanOrEqual(1);
    expect(component.getPasswordStrengthClass()).toBe('password-strength-weak');
    expect(component.getPasswordStrengthLabel()).toBe('Weak');

    // Test medium password
    passwordControl?.setValue('Medium');
    expect(component.getPasswordStrengthClass()).toBe('password-strength-medium');
    expect(component.getPasswordStrengthLabel()).toBe('Medium');

    // Test strong password
    passwordControl?.setValue('StrongPass123!');
    expect(component.getPasswordStrengthClass()).toBe('password-strength-strong');
    expect(component.getPasswordStrengthLabel()).toBe('Strong');
  });

  it('should validate password match', () => {
    component.form.patchValue({
      password: 'ValidPass123!',
      confirm_password: 'DifferentPass456!'
    });

    expect(component.form.valid).toBeFalsy();
    expect(component.form.errors?.['passwordMismatch']).toBeFalsy(); // Will be on confirm_password control

    const confirmControl = component.form.get('confirm_password');
    expect(confirmControl?.errors?.['passwordMismatch']).toBeTruthy();
  });

  it('should submit form successfully when valid', () => {
    spyOn(userService, 'createUser').and.returnValue(of({
      id: 1,
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      user_type: 'employee',
      is_active: true,
      is_superuser: false,
      employee_id: 'EMP123456',
      avatar: null,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z'
    } as User));

    component.form.patchValue({
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      user_type: 'employee',
      is_active: true,
      password: 'ValidPass123!',
      confirm_password: 'ValidPass123!'
    });

    spyOn(component['snackBar'], 'open');

    component.onSubmit();

    expect(userService.createUser).toHaveBeenCalledWith({
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      user_type: 'employee',
      is_active: true,
      password: 'ValidPass123!'
    });

    expect(mockDialogRef.close).toHaveBeenCalledWith(jasmine.any(Object));
    expect(component['snackBar'].open).toHaveBeenCalledWith(
      'User created successfully',
      'Close',
      { duration: 3000 }
    );
  });

  it('should show error when form submission fails', () => {
    spyOn(userService, 'createUser').and.returnValue(throwError({
      error: { detail: 'Email already exists' }
    }));

    component.form.patchValue({
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      user_type: 'employee',
      is_active: true,
      password: 'ValidPass123!',
      confirm_password: 'ValidPass123!'
    });

    spyOn(component['snackBar'], 'open');

    component.onSubmit();

    expect(component['snackBar'].open).toHaveBeenCalledWith(
      'Error creating user: Email already exists',
      'Close',
      { duration: 3000 }
    );
  });

  it('should close dialog when cancel is clicked', () => {
    component.onCancel();
    expect(mockDialogRef.close).toHaveBeenCalled();
  });

  it('should have proper form validation', () => {
    const emailControl = component.form.get('email');
    const firstNameControl = component.form.get('first_name');
    const lastNameControl = component.form.get('last_name');

    // Initially invalid
    expect(component.form.valid).toBeFalsy();

    // Email validation
    emailControl?.setValue('invalid-email');
    expect(emailControl?.valid).toBeFalsy();

    emailControl?.setValue('valid@example.com');
    expect(emailControl?.valid).toBeTruthy();

    // Name validation
    firstNameControl?.setValue('');
    expect(firstNameControl?.valid).toBeFalsy();

    firstNameControl?.setValue('Valid');
    expect(firstNameControl?.valid).toBeTruthy();

    lastNameControl?.setValue('');
    expect(lastNameControl?.valid).toBeFalsy();

    lastNameControl?.setValue('Valid');
    expect(lastNameControl?.valid).toBeTruthy();
  });
});