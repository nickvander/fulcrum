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
import { UserService } from '../../services/user.service';
import { User } from '../../models/user.model';
import { MatSnackBar } from '@angular/material/snack-bar';

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
  ],
})
export class UserForm implements OnInit {
  form: FormGroup;
  user!: User;
  isEdit: boolean = false;
  passwordRequired: boolean = true; // For new users, password is required

  constructor(
    private fb: FormBuilder,
    private userService: UserService,
    private route: ActivatedRoute,
    private router: Router,
    private snackBar: MatSnackBar
  ) {
    this.form = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      first_name: ['', Validators.required],
      last_name: ['', Validators.required],
      user_type: ['employee', Validators.required],
      is_active: [true],
      is_superuser: [false],
      password: ['', []], // Optional for edits, required for new users
      confirm_password: ['', []],
    }, { validators: this.passwordMatchValidator });
  }

  ngOnInit(): void {
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
            this.snackBar.open(`Error updating user: ${error.message || 'Unknown error'}`, 'Close', { duration: 3000 });
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
            this.snackBar.open(`Error creating user: ${error.message || 'Unknown error'}`, 'Close', { duration: 3000 });
          }
        });
      }
    } else {
      this.snackBar.open('Please fill in all required fields correctly', 'Close', { duration: 3000 });
    }
  }

  onCancel(): void {
    this.router.navigate(['/users']);
  }
}
