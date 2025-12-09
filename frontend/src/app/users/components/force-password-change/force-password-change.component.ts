import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { UserService } from '../../services/user.service';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
    selector: 'app-force-password-change',
    standalone: true,
    imports: [
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatSnackBarModule
],
    template: `
    <div class="container">
      <mat-card>
        <mat-card-header>
          <mat-card-title>Change Password Required</mat-card-title>
          <mat-card-subtitle>For security reasons, you must change your password before proceeding.</mat-card-subtitle>
        </mat-card-header>
        <mat-card-content>
          <form [formGroup]="passwordForm" (ngSubmit)="onSubmit()">
            <mat-form-field appearance="fill" class="full-width">
              <mat-label>Current Password</mat-label>
              <input matInput [type]="hideCurrent ? 'password' : 'text'" formControlName="currentPassword">
              <button mat-icon-button matSuffix (click)="hideCurrent = !hideCurrent" [attr.aria-label]="'Hide password'" [attr.aria-pressed]="hideCurrent" type="button">
                <mat-icon>{{hideCurrent ? 'visibility_off' : 'visibility'}}</mat-icon>
              </button>
              @if (passwordForm.get('currentPassword')?.hasError('required')) {
                <mat-error>
                  Current password is required
                </mat-error>
              }
            </mat-form-field>
    
            <mat-form-field appearance="fill" class="full-width">
              <mat-label>New Password</mat-label>
              <input matInput [type]="hideNew ? 'password' : 'text'" formControlName="newPassword">
              <button mat-icon-button matSuffix (click)="hideNew = !hideNew" [attr.aria-label]="'Hide password'" [attr.aria-pressed]="hideNew" type="button">
                <mat-icon>{{hideNew ? 'visibility_off' : 'visibility'}}</mat-icon>
              </button>
              @if (passwordForm.get('newPassword')?.hasError('required')) {
                <mat-error>
                  New password is required
                </mat-error>
              }
              @if (passwordForm.get('newPassword')?.hasError('minlength')) {
                <mat-error>
                  Password must be at least 8 characters
                </mat-error>
              }
            </mat-form-field>
    
            <mat-form-field appearance="fill" class="full-width">
              <mat-label>Confirm New Password</mat-label>
              <input matInput [type]="hideConfirm ? 'password' : 'text'" formControlName="confirmPassword">
              <button mat-icon-button matSuffix (click)="hideConfirm = !hideConfirm" [attr.aria-label]="'Hide password'" [attr.aria-pressed]="hideConfirm" type="button">
                <mat-icon>{{hideConfirm ? 'visibility_off' : 'visibility'}}</mat-icon>
              </button>
              @if (passwordForm.get('confirmPassword')?.hasError('required')) {
                <mat-error>
                  Confirm password is required
                </mat-error>
              }
              @if (passwordForm.hasError('mismatch')) {
                <mat-error>
                  Passwords do not match
                </mat-error>
              }
            </mat-form-field>
    
            <div class="actions">
              <button mat-raised-button color="primary" type="submit" [disabled]="passwordForm.invalid || isLoading">
                {{ isLoading ? 'Updating...' : 'Update Password' }}
              </button>
            </div>
          </form>
        </mat-card-content>
      </mat-card>
    </div>
    `,
    styles: [`
    .container {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      background-color: #f5f5f5;
    }
    mat-card {
      max-width: 400px;
      width: 100%;
      padding: 20px;
    }
    .full-width {
      width: 100%;
      margin-bottom: 10px;
    }
    .actions {
      display: flex;
      justify-content: flex-end;
      margin-top: 20px;
    }
  `]
})
export class ForcePasswordChangeComponent implements OnInit {
    passwordForm: FormGroup;
    hideCurrent = true;
    hideNew = true;
    hideConfirm = true;
    isLoading = false;

    constructor(
        private fb: FormBuilder,
        private userService: UserService,
        private router: Router,
        private snackBar: MatSnackBar
    ) {
        this.passwordForm = this.fb.group({
            currentPassword: ['', Validators.required],
            newPassword: ['', [Validators.required, Validators.minLength(8)]],
            confirmPassword: ['', Validators.required]
        }, { validator: this.passwordMatchValidator });
    }

    ngOnInit(): void { }

    passwordMatchValidator(g: FormGroup) {
        return g.get('newPassword')?.value === g.get('confirmPassword')?.value
            ? null : { 'mismatch': true };
    }

    onSubmit(): void {
        if (this.passwordForm.valid) {
            this.isLoading = true;
            const { currentPassword, newPassword } = this.passwordForm.value;

            this.userService.changePassword(currentPassword, newPassword).subscribe({
                next: () => {
                    this.isLoading = false;
                    this.snackBar.open('Password updated successfully', 'Close', { duration: 3000 });
                    this.router.navigate(['/']); // Navigate to home/dashboard
                },
                error: (error) => {
                    this.isLoading = false;
                    let errorMessage = 'Failed to update password';
                    if (error.error && error.error.detail) {
                        errorMessage = error.error.detail;
                    }
                    this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
                }
            });
        }
    }
}
