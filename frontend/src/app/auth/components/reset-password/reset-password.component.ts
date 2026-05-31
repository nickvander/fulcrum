
import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { AuthService } from '../../../core/services/auth.service';
import { translateApiError } from '../../../core/errors/translate-api-error';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'app-reset-password',
    templateUrl: './reset-password.component.html',
    styleUrls: ['./reset-password.component.scss'],
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, RouterModule, TranslocoModule]
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
        private authService: AuthService,
        private transloco: TranslocoService,
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
            this.error = this.transloco.translate('auth.resetPassword.errors.invalidToken');
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
            this.error = this.transloco.translate('auth.resetPassword.errors.missingToken');
            return;
        }

        this.isLoading = true;
        this.authService.resetPassword(this.token, this.f['password'].value)
            .subscribe({
                next: (response) => {
                    this.isLoading = false;
                    this.message = this.transloco.translate('auth.resetPassword.successMessage');
                    setTimeout(() => {
                        this.router.navigate(['/login']);
                    }, 3000);
                },
                error: (error) => {
                    this.isLoading = false;
                    this.error = translateApiError(error, this.transloco, 'apiErrors.unknown');
                }
            });
    }
}
