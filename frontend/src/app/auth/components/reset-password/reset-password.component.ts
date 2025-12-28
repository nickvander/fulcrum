
import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'app-reset-password',
    templateUrl: './reset-password.component.html',
    styleUrls: ['./reset-password.component.scss'],
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, RouterModule]
})
export class ResetPasswordComponent implements OnInit {
    resetPasswordForm: FormGroup;
    isLoading = false;
    message = '';
    error = '';
    submitted = false;
    token = '';

    constructor(
        private formBuilder: FormBuilder,
        private route: ActivatedRoute,
        private router: Router,
        private authService: AuthService
    ) {
        this.resetPasswordForm = this.formBuilder.group({
            password: ['', [Validators.required, Validators.minLength(8)]],
            confirmPassword: ['', Validators.required]
        }, {
            validator: this.passwordMatchValidator
        });
    }

    ngOnInit() {
        this.token = this.route.snapshot.queryParams['token'];
        if (!this.token) {
            this.error = 'Invalid password reset token.';
        }
    }

    passwordMatchValidator(form: FormGroup) {
        const password = form.get('password');
        const confirmPassword = form.get('confirmPassword');

        if (password && confirmPassword && password.value !== confirmPassword.value) {
            confirmPassword.setErrors({ passwordMismatch: true });
        } else {
            confirmPassword?.setErrors(null);
        }
        return null;
    }

    get f() { return this.resetPasswordForm.controls; }

    onSubmit() {
        this.submitted = true;
        this.message = '';
        this.error = '';

        if (this.resetPasswordForm.invalid) {
            return;
        }

        if (!this.token) {
            this.error = 'Missing reset token.';
            return;
        }

        this.isLoading = true;
        this.authService.resetPassword(this.token, this.f['password'].value)
            .subscribe({
                next: (response) => {
                    this.isLoading = false;
                    this.message = 'Password has been reset successfully. Redirecting to login...';
                    setTimeout(() => {
                        this.router.navigate(['/login']);
                    }, 3000);
                },
                error: (error) => {
                    this.isLoading = false;
                    this.error = error.error?.detail || 'An error occurred. Please try again.';
                }
            });
    }
}
