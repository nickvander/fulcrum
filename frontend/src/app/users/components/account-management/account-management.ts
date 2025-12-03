import { Component, OnInit, OnDestroy } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { UserService } from '../../services/user.service';
import { User } from '../../../shared/models/user.model';
import { Subject, takeUntil } from 'rxjs';

@Component({
  selector: 'app-account-management',
  templateUrl: './account-management.html',
  styleUrls: ['./account-management.scss'],
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSnackBarModule,
  ],
})
export class AccountManagement implements OnInit, OnDestroy {
  form: FormGroup;
  user: User | null = null;
  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private userService: UserService,
    private snackBar: MatSnackBar
  ) {
    this.form = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      first_name: ['', Validators.required],
      last_name: ['', Validators.required],
    });
  }

  ngOnInit(): void {
    this.loadUserProfile();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadUserProfile(): void {
    this.userService.getProfile()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (user: User) => {
          this.user = user;
          this.form.patchValue({
            email: user.email,
            first_name: user.first_name,
            last_name: user.last_name,
          });
        },
        error: (error: any) => {
          // Error handling is now in the HTTP interceptor, so the error message
          // should already be displayed via the interceptor
          console.error('Error loading profile:', error);
        }
      });
  }

  onSubmit(): void {
    if (this.form.valid && this.user) {
      const updateData = { ...this.form.value };

      this.userService.updateProfile(updateData)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (updatedUser: User) => {
            this.user = updatedUser;
            this.snackBar.open('Profile updated successfully', 'Close', { duration: 3000 });
          },
          error: (error: any) => {
            // Error handling is now in the HTTP interceptor, so the error message
            // should already be displayed via the interceptor
            console.error('Error updating profile:', error);
          }
        });
    }
  }

  onCancel(): void {
    this.loadUserProfile(); // Reset form to current values
  }
}