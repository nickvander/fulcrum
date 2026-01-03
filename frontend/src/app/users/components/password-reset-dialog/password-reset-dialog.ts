import { Component, Inject, OnDestroy } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, AbstractControl } from '@angular/forms';

import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDialog, MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { UserService } from '../../services/user.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { GeneratedPasswordDialog } from '../generated-password-dialog/generated-password-dialog';
import { Subject, takeUntil } from 'rxjs';

@Component({
  selector: 'app-password-reset-dialog',
  templateUrl: './password-reset-dialog.html',
  styleUrls: ['./password-reset-dialog.scss'],
  standalone: true,
  imports: [
    MatDialogModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    TranslocoModule
  ],
})
export class PasswordResetDialog implements OnDestroy {
  form: FormGroup;
  private destroy$ = new Subject<void>();

  constructor(
    public dialogRef: MatDialogRef<PasswordResetDialog>,
    @Inject(MAT_DIALOG_DATA) public data: { userId: number, email: string, isForAdmin?: boolean },
    private fb: FormBuilder,
    private userService: UserService,
    private snackBar: MatSnackBar,
    private dialog: MatDialog,
    private translocoService: TranslocoService
  ) {
    // For admin resets, we don't need password input fields as the system generates a random password
    if (data.isForAdmin) {
      this.form = this.fb.group({});
    } else {
      this.form = this.fb.group({
        newPassword: ['', [Validators.required, this.strongPasswordValidator]],
        confirmNewPassword: ['', Validators.required],
      }, { validators: this.passwordMatchValidator });
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
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
    if (this.data.isForAdmin) {
      // For admin reset, call the admin reset endpoint
      this.userService.adminResetPassword(this.data.userId)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (response) => {
            if (response.new_password) {
              // Show the generated password in a dedicated dialog with user email
              const passwordDialogRef = this.dialog.open(GeneratedPasswordDialog, {
                width: '500px',
                data: {
                  password: response.new_password,
                  userEmail: this.data.email
                }
              });

              // Close the password reset dialog after showing the generated password dialog
              this.dialogRef.close({ success: true, newPassword: response.new_password });
            } else {
              this.snackBar.open(this.translocoService.translate('users.messages.resetSuccess'), this.translocoService.translate('common.close'), {
                duration: 5000,
              });
              this.dialogRef.close({ success: true });
            }
          },
          error: (error) => {
            // Error handling is now in the HTTP interceptor, so the error message
            // should already be displayed via the interceptor
            console.error('Error resetting password:', error);
          }
        });
    } else if (this.form.valid) {
      // For user reset, we would need the token - this is for self-initiated reset
      // However, since admin shouldn't be doing user's token-based reset, we'll just show an appropriate message
      this.snackBar.open(this.translocoService.translate('users.errors.adminResetOnly'), this.translocoService.translate('common.close'), {
        duration: 5000,
      });
      this.dialogRef.close();
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}