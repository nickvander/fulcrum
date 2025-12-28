
import { Component } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

@Component({
    selector: 'app-forgot-password',
    templateUrl: './forgot-password.component.html',
    styleUrls: ['./forgot-password.component.scss'],
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, RouterModule]
})
export class ForgotPasswordComponent {
    forgotPasswordForm: FormGroup;
    isLoading = false;
    message = '';
    error = '';
    submitted = false;

    constructor(
        private formBuilder: FormBuilder,
        private authService: AuthService
    ) {
        this.forgotPasswordForm = this.formBuilder.group({
            email: ['', [Validators.required, Validators.email]]
        });
    }

    get f() { return this.forgotPasswordForm.controls; }

    onSubmit() {
        this.submitted = true;
        this.message = '';
        this.error = '';

        if (this.forgotPasswordForm.invalid) {
            return;
        }

        this.isLoading = true;
        this.authService.requestPasswordReset(this.f['email'].value)
            .subscribe({
                next: (response) => {
                    this.isLoading = false;
                    this.message = response.message || 'If the email exists, a reset link has been sent.';
                },
                error: (error) => {
                    this.isLoading = false;
                    // For security, we might want to show the same message even on error, 
                    // but for now let's show a generic error or what the backend returns if safe.
                    // The backend returns "If the email exists..." even if not found, so this error block 
                    // would likely be for network issues or 500s.
                    this.error = 'An error occurred. Please try again later.';
                }
            });
    }
}
