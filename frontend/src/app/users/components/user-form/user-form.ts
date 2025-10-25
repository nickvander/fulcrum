import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, AbstractControl } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { UserService } from '../../services/user.service';
import { User } from '../../models/user.model';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-user-form',
  templateUrl: './user-form.html',
  styleUrls: ['./user-form.scss'],
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSlideToggleModule,
    MatSelectModule,
    MatButtonModule,
    MatSnackBarModule,
    MatTooltipModule,
  ],
})
export class UserForm implements OnInit {
  form: FormGroup;
  user!: User;
  isEdit: boolean = false;
  passwordRequired: boolean = true; // For new users, password is required
  isCurrentUserAdmin: boolean = false;

  constructor(
    private fb: FormBuilder,
    private userService: UserService,
    private route: ActivatedRoute,
    private router: Router,
    private snackBar: MatSnackBar,
    private authService: AuthService
  ) {
    this.form = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      first_name: ['', Validators.required],
      last_name: ['', Validators.required],
      user_type: ['employee', Validators.required],
      avatar: [''],
      is_active: [true],
      is_superuser: [false],
      password: ['', []], // Optional for edits, required for new users
      confirm_password: ['', []],
    }, { validators: this.passwordMatchValidator });
  }

  ngOnInit(): void {
    // Check if current user is admin to determine visibility of superuser toggle
    // Add defensive check to prevent errors in test environments
    try {
      if (this.authService && typeof this.authService.isAdmin === 'function') {
        const isAdminObservable = this.authService.isAdmin();
        if (isAdminObservable && typeof isAdminObservable.subscribe === 'function') {
          isAdminObservable.subscribe({
            next: (isAdmin) => {
              this.isCurrentUserAdmin = isAdmin;
            },
            error: (error) => {
              console.warn('Error checking admin status:', error);
              this.isCurrentUserAdmin = false;
            }
          });
        } else {
          // Fallback for test environments or when authService returns undefined
          this.isCurrentUserAdmin = false;
        }
      } else {
        // Fallback for test environments or when authService is not properly initialized
        this.isCurrentUserAdmin = false;
      }
    } catch (error) {
      // Catch any unexpected errors and set a default value
      console.warn('Error checking admin status:', error);
      this.isCurrentUserAdmin = false;
    }

    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEdit = true;
      this.passwordRequired = false; // Password not required when editing
      // Remove required validation from password fields for edits
      this.form.get('password')?.clearValidators();
      this.form.get('confirm_password')?.clearValidators();
      
      this.userService.getUser(+id).subscribe({
        next: (user) => {
          this.user = user;
          // Set form values but exclude password fields when editing
          this.form.patchValue({
            email: user.email,
            first_name: user.first_name,
            last_name: user.last_name,
            user_type: user.user_type,
            is_active: user.is_active,
            is_superuser: user.is_superuser,
          });
        },
        error: (error) => {
          this.snackBar.open('Error loading user data', 'Close', { duration: 3000 });
          this.router.navigate(['/users']);
        }
      });
    } else {
      // For new users, password is required
      this.form.get('password')?.setValidators([Validators.required, this.strongPasswordValidator]);
      this.form.get('confirm_password')?.setValidators([Validators.required]);
    }
  }

  passwordMatchValidator(form: FormGroup) {
    const password = form.get('password');
    const confirmPassword = form.get('confirm_password');
    if (password && confirmPassword && password.value !== confirmPassword.value) {
      confirmPassword.setErrors({ passwordMismatch: true });
    } else {
      confirmPassword?.setErrors(null);
    }
    return null;
  }

  strongPasswordValidator(control: AbstractControl) {
    const value = control.value;
    if (!value) return null;

    const hasUpperCase = /[A-Z]/.test(value);
    const hasLowerCase = /[a-z]/.test(value);
    const hasNumbers = /\d/.test(value);
    const hasSpecialChar = /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(value);
    const isLongEnough = value.length >= 8;

    const isValid = hasUpperCase && hasLowerCase && hasNumbers && hasSpecialChar && isLongEnough;
    
    return isValid ? null : { weakPassword: true };
  }

  onSubmit(): void {
    if (this.form.valid) {
      const formValue = { ...this.form.value };
      
      // Remove confirm_password from the submission
      delete formValue.confirm_password;
      
      // Ensure non-empty password is provided when required
      if (this.isEdit && !formValue.password) {
        delete formValue.password; // Don't send empty password on update
      }

      if (this.isEdit) {
        // Update existing user
        this.userService.updateUser(this.user.id, formValue).subscribe({
          next: () => {
            this.snackBar.open('User updated successfully', 'Close', { duration: 3000 });
            this.router.navigate(['/users']);
          },
          error: (error) => {
            // Error handling is now in the HTTP interceptor, so the error message
            // should already be displayed via the interceptor
            console.error('Error updating user:', error);
          }
        });
      } else {
        // Create new user
        this.userService.createUser(formValue).subscribe({
          next: (user) => {
            this.snackBar.open('User created successfully', 'Close', { duration: 3000 });
            this.router.navigate(['/users']);
          },
          error: (error) => {
            // Error handling is now in the HTTP interceptor, so the error message
            // should already be displayed via the interceptor
            console.error('Error creating user:', error);
          }
        });
      }
    } else {
      this.snackBar.open('Please fill in all required fields correctly', 'Close', { duration: 3000 });
    }
  }

  getPasswordStrength(password: string): number {
    if (!password) return 0;
    
    let strength = 0;
    
    // Length check
    if (password.length >= 8) strength += 1;
    if (password.length >= 12) strength += 1;
    
    // Character variety checks
    if (/[a-z]/.test(password)) strength += 1;
    if (/[A-Z]/.test(password)) strength += 1;
    if (/[0-9]/.test(password)) strength += 1;
    if (/[^A-Za-z0-9]/.test(password)) strength += 1;
    
    return Math.min(strength, 4); // Max strength is 4
  }

  getPasswordStrengthClass(): string {
    const password = this.form.get('password')?.value;
    const strength = this.getPasswordStrength(password);
    
    if (strength <= 1) return 'password-strength-weak';
    if (strength <= 2) return 'password-strength-medium';
    return 'password-strength-strong';
  }

  getPasswordStrengthLabel(): string {
    const password = this.form.get('password')?.value;
    const strength = this.getPasswordStrength(password);
    
    if (strength <= 1) return 'Weak';
    if (strength <= 2) return 'Medium';
    if (strength >= 3) return 'Strong';
    return '';
  }

  onSaveAndAddAnother(): void {
    if (this.form.valid && !this.isEdit) { // Only for new users
      const formValue = { ...this.form.value };
      
      // Remove confirm_password from the submission
      delete formValue.confirm_password;
      
      this.userService.createUser(formValue).subscribe({
        next: (user) => {
          this.snackBar.open('User created successfully', 'Close', { duration: 3000 });
          
          // Reset form for new user creation
          this.form.reset();
          this.form.patchValue({
            user_type: 'employee',
            is_active: true,
            is_superuser: false
          });
          
          // Keep focus on first field for better UX
          setTimeout(() => {
            const firstInput = document.querySelector('input') as HTMLInputElement;
            if (firstInput) firstInput.focus();
          }, 100);
        },
        error: (error) => {
          // Error handling is now in the HTTP interceptor
          console.error('Error creating user:', error);
        }
      });
    }
  }

  onCancel(): void {
    this.router.navigate(['/users']);
  }
}
