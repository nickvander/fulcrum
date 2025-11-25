import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, AbstractControl } from '@angular/forms';
import { MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { CommonModule } from '@angular/common';
import { UserService } from '../../services/user.service';
import { User } from '../../models/user.model';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-user-create-modal',
  templateUrl: './user-create-modal.html',
  styleUrls: ['./user-create-modal.scss'],
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatSlideToggleModule,
    MatDialogModule,
  ],
})
export class UserCreateModal implements OnInit {
  form: FormGroup;
  passwordRequired: boolean = true;

  constructor(
    public dialogRef: MatDialogRef<UserCreateModal>,
    private fb: FormBuilder,
    private userService: UserService,
    private snackBar: MatSnackBar
  ) {
    this.form = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      first_name: ['', Validators.required],
      last_name: ['', Validators.required],
      user_type: ['employee', Validators.required],
      is_active: [true],
      password: ['', [Validators.required, this.strongPasswordValidator]],
      confirm_password: ['', [Validators.required]],
    }, { validators: this.passwordMatchValidator });
  }

  ngOnInit(): void { }

  passwordMatchValidator(form: FormGroup) {
    const password = form.get('password');
    const confirm_password = form.get('confirm_password');
    if (password && confirm_password && password.value !== confirm_password.value) {
      confirm_password.setErrors({ passwordMismatch: true });
    } else {
      confirm_password?.setErrors(null);
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

      this.userService.createUser(formValue).subscribe({
        next: (user: User) => {
          this.snackBar.open('User created successfully', 'Close', { duration: 3000 });
          this.dialogRef.close(user);
        },
        error: (error) => {
          this.snackBar.open('Error creating user: ' + error.error.detail, 'Close', { duration: 3000 });
        }
      });
    } else {
      this.snackBar.open('Please fill in all required fields correctly', 'Close', { duration: 3000 });
    }
  }

  onCancel(): void {
    this.dialogRef.close();
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
}