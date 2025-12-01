import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ResetPasswordComponent } from './reset-password.component';
import { AuthService } from '../../services/auth';
import { of, throwError } from 'rxjs';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router } from '@angular/router';

describe('ResetPasswordComponent', () => {
    let component: ResetPasswordComponent;
    let fixture: ComponentFixture<ResetPasswordComponent>;
    let authServiceSpy: jasmine.SpyObj<AuthService>;
    let routerSpy: jasmine.SpyObj<Router>;

    beforeEach(async () => {
        const authSpy = jasmine.createSpyObj('AuthService', ['resetPassword']);
        const rSpy = jasmine.createSpyObj('Router', ['navigate', 'createUrlTree', 'serializeUrl']);
        rSpy.events = of(null); // Mock events observable

        await TestBed.configureTestingModule({
            imports: [ResetPasswordComponent, BrowserAnimationsModule],
            providers: [
                { provide: AuthService, useValue: authSpy },
                { provide: Router, useValue: rSpy },
                {
                    provide: ActivatedRoute,
                    useValue: {
                        snapshot: { queryParams: { token: 'valid-token' } }
                    }
                }
            ]
        }).compileComponents();

        authServiceSpy = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
        routerSpy = TestBed.inject(Router) as jasmine.SpyObj<Router>;
        fixture = TestBed.createComponent(ResetPasswordComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should initialize with token from route', () => {
        expect(component.token).toBe('valid-token');
    });

    it('should call resetPassword on submit with valid form', () => {
        component.resetPasswordForm.controls['password'].setValue('newpassword123');
        component.resetPasswordForm.controls['confirmPassword'].setValue('newpassword123');
        authServiceSpy.resetPassword.and.returnValue(of({ message: 'Success' }));

        jasmine.clock().install();
        component.onSubmit();

        expect(authServiceSpy.resetPassword).toHaveBeenCalledWith('valid-token', 'newpassword123');
        expect(component.message).toBe('Password has been reset successfully. Redirecting to login...');

        jasmine.clock().tick(3001);
        expect(routerSpy.navigate).toHaveBeenCalledWith(['/login']);
        jasmine.clock().uninstall();
    });

    it('should handle error on submit', () => {
        component.resetPasswordForm.controls['password'].setValue('newpassword123');
        component.resetPasswordForm.controls['confirmPassword'].setValue('newpassword123');
        authServiceSpy.resetPassword.and.returnValue(throwError(() => ({ error: { detail: 'Error detail' } })));

        component.onSubmit();

        expect(authServiceSpy.resetPassword).toHaveBeenCalled();
        expect(component.error).toBe('Error detail');
    });

    it('should validate password match', () => {
        component.resetPasswordForm.controls['password'].setValue('password123');
        component.resetPasswordForm.controls['confirmPassword'].setValue('different');

        // Trigger validation
        component.resetPasswordForm.updateValueAndValidity();

        expect(component.resetPasswordForm.controls['confirmPassword'].hasError('passwordMismatch')).toBeTrue();
    });
});
