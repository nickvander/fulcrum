import type { MockedObject } from "vitest";
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ForgotPasswordComponent } from './forgot-password.component';
import { AuthService } from '../../services/auth';
import { of, throwError } from 'rxjs';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute } from '@angular/router';

describe('ForgotPasswordComponent', () => {
    let component: ForgotPasswordComponent;
    let fixture: ComponentFixture<ForgotPasswordComponent>;
    let authServiceSpy: MockedObject<AuthService>;

    beforeEach(async () => {
        const spy = {
            requestPasswordReset: vi.fn().mockName("AuthService.requestPasswordReset")
        };

        await TestBed.configureTestingModule({
            imports: [ForgotPasswordComponent, BrowserAnimationsModule],
            providers: [
                { provide: AuthService, useValue: spy },
                { provide: ActivatedRoute, useValue: {} }
            ]
        }).compileComponents();

        authServiceSpy = TestBed.inject(AuthService) as MockedObject<AuthService>;
        fixture = TestBed.createComponent(ForgotPasswordComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should call requestPasswordReset on submit with valid email', () => {
        const email = 'test@example.com';
        component.forgotPasswordForm.controls['email'].setValue(email);
        authServiceSpy.requestPasswordReset.mockReturnValue(of({ message: 'Success' }));

        component.onSubmit();

        expect(authServiceSpy.requestPasswordReset).toHaveBeenCalledWith(email);
        expect(component.message).toBe('Success');
        expect(component.isLoading).toBe(false);
    });

    it('should handle error on submit', () => {
        const email = 'test@example.com';
        component.forgotPasswordForm.controls['email'].setValue(email);
        authServiceSpy.requestPasswordReset.mockReturnValue(throwError(() => new Error('Error')));

        component.onSubmit();

        expect(authServiceSpy.requestPasswordReset).toHaveBeenCalledWith(email);
        expect(component.error).toBe('An error occurred. Please try again later.');
        expect(component.isLoading).toBe(false);
    });

    it('should not call requestPasswordReset if form is invalid', () => {
        component.forgotPasswordForm.controls['email'].setValue('');
        component.onSubmit();
        expect(authServiceSpy.requestPasswordReset).not.toHaveBeenCalled();
    });
});
