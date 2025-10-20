import { Component, Inject } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, AbstractControl } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { UserService } from '../../services/user.service';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-password-reset-dialog',
  templateUrl: './password-reset-dialog.html',
  styleUrls: ['./password-reset-dialog.scss'],
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
  ],
})
export class PasswordResetDialog {
  form: FormGroup;

  constructor(
    public dialogRef: MatDialogRef<PasswordResetDialog>,
    @Inject(MAT_DIALOG_DATA) public data: { userId: number, email: string },
    private fb: FormBuilder,
    private userService: UserService,
    private snackBar: MatSnackBar
  ) {
    this.form = this.fb.group({
      newPassword: ['', [Validators.required, this.strongPasswordValidator]],
      confirmNewPassword: ['', Validators.required],
    }, { validators: this.passwordMatchValidator });
  }

  passwordMatchValidator(form: FormGroup) {
    const newPassword = form.get('newPassword');
    const confirmNewPassword = form.get('confirmNewPassword');
    if (newPassword && confirmNewPassword && newPassword.value !== confirmNewPassword.value) {
      confirmNewPassword.setErrors({ passwordMismatch: true });
    } else {
      confirmNewPassword?.setErrors(null);
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
      // Here you would implement the password reset logic
      // This would typically involve an API call to reset the user's password
      console.log('Resetting password for user:', this.data.userId);
      this.dialogRef.close({ success: true });
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}