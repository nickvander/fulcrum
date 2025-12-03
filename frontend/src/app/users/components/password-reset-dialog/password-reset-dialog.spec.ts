import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { PasswordResetDialog } from './password-reset-dialog';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialog, MatDialogModule } from '@angular/material/dialog';
import { UserService } from '../../services/user.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ReactiveFormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { GeneratedPasswordDialog } from '../generated-password-dialog/generated-password-dialog';

describe('PasswordResetDialog', () => {
    let component: PasswordResetDialog;
    let fixture: ComponentFixture<PasswordResetDialog>;
    let dialogRefMock: jasmine.SpyObj<MatDialogRef<PasswordResetDialog>>;
    let userServiceMock: jasmine.SpyObj<UserService>;
    let snackBarMock: jasmine.SpyObj<MatSnackBar>;
    let dialogMock: jasmine.SpyObj<MatDialog>;

    const mockData = { userId: 1, email: 'test@example.com', isForAdmin: true };

    beforeEach(async () => {
        dialogRefMock = jasmine.createSpyObj('MatDialogRef', ['close']);
        userServiceMock = jasmine.createSpyObj('UserService', ['adminResetPassword']);
        snackBarMock = jasmine.createSpyObj('MatSnackBar', ['open']);
        dialogMock = jasmine.createSpyObj('MatDialog', ['open']);

        await TestBed.configureTestingModule({
            imports: [
                PasswordResetDialog,
                ReactiveFormsModule,
                NoopAnimationsModule
            ],
            providers: [
                { provide: MatDialogRef, useValue: dialogRefMock },
                { provide: MAT_DIALOG_DATA, useValue: mockData },
                { provide: UserService, useValue: userServiceMock },
                { provide: MatSnackBar, useValue: snackBarMock },
                { provide: MatDialog, useValue: dialogMock }
            ],
            schemas: [CUSTOM_ELEMENTS_SCHEMA]
        })
            .overrideComponent(PasswordResetDialog, {
                remove: { imports: [MatDialogModule] },
                add: { schemas: [CUSTOM_ELEMENTS_SCHEMA] }
            })
            .compileComponents();

        fixture = TestBed.createComponent(PasswordResetDialog);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should initialize empty form for admin', () => {
        expect(component.form.controls['newPassword']).toBeUndefined();
    });

    it('should call adminResetPassword on submit', () => {
        const mockResponse = { new_password: 'GeneratedPassword123!', message: 'Success' };
        userServiceMock.adminResetPassword.and.returnValue(of(mockResponse));
        dialogMock.open.and.returnValue({ afterClosed: () => of(true) } as any);

        component.onSubmit();

        expect(userServiceMock.adminResetPassword).toHaveBeenCalledWith(mockData.userId);
        expect(dialogMock.open).toHaveBeenCalledWith(GeneratedPasswordDialog, jasmine.objectContaining({
            data: { password: mockResponse.new_password, userEmail: mockData.email }
        }));
        expect(dialogRefMock.close).toHaveBeenCalledWith({ success: true, newPassword: mockResponse.new_password });
    });

    it('should close dialog on cancel', () => {
        component.onCancel();
        expect(dialogRefMock.close).toHaveBeenCalled();
    });
});
