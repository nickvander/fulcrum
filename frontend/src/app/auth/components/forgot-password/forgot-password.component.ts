
import { Component } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';

@Component({
    selector: 'app-forgot-password',
    templateUrl: './forgot-password.component.html',
    styleUrls: ['./forgot-password.component.scss'],
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, RouterModule, TranslocoModule]
})
export class ForgotPasswordComponent {
    forgotPasswordForm: FormGroup;
    isLoading = false;
    message = '';
    error = '';
    submitted = false;

    constructor(
        private formBuilder: FormBuilder,
        private authService: AuthService,
        private transloco: TranslocoService
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
                    this.message = response.message || this.transloco.translate('auth.forgotPassword.successMessage');
                },
                error: (error) => {
                    this.isLoading = false;
                    // For security, we might want to show the same message even on error, 
                    // but for now let's show a generic error or what the backend returns if safe.
                    // The backend returns "If the email exists..." even if not found, so this error block 
                    // would likely be for network issues or 500s.
                    this.error = this.transloco.translate('auth.forgotPassword.errorMessage');
                }
            });
    }
}
