import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AccountManagement } from './account-management';
import { UserService } from '../../services/user.service';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ReactiveFormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { User } from '../../../shared/models/user.model';

describe('AccountManagement', () => {
    let component: AccountManagement;
    let fixture: ComponentFixture<AccountManagement>;
    let userServiceMock: jasmine.SpyObj<UserService>;
    let snackBarMock: jasmine.SpyObj<MatSnackBar>;

    const mockUser: User = {
        id: 1,
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
        user_type: 'admin',
        is_active: true,
        is_superuser: false,
        force_password_change: false,
        employee_id: null
    };

    beforeEach(async () => {
        userServiceMock = jasmine.createSpyObj('UserService', ['getProfile', 'updateProfile']);
        snackBarMock = jasmine.createSpyObj('MatSnackBar', ['open']);

        userServiceMock.getProfile.and.returnValue(of(mockUser));
        userServiceMock.updateProfile.and.returnValue(of(mockUser));

        await TestBed.configureTestingModule({
            imports: [
                AccountManagement,
                ReactiveFormsModule,
                NoopAnimationsModule
            ],
            providers: [
                { provide: UserService, useValue: userServiceMock },
                { provide: MatSnackBar, useValue: snackBarMock }
            ]
        })
            .overrideComponent(AccountManagement, {
                remove: { imports: [MatSnackBarModule] }
            })
            .compileComponents();

        fixture = TestBed.createComponent(AccountManagement);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should load user profile on init', () => {
        expect(userServiceMock.getProfile).toHaveBeenCalled();
        expect(component.user).toEqual(mockUser);
        expect(component.form.value).toEqual({
            email: mockUser.email,
            first_name: mockUser.first_name,
            last_name: mockUser.last_name
        });
    });

    it('should update profile on submit', () => {
        const updatedUser = { ...mockUser, first_name: 'Updated' };
        userServiceMock.updateProfile.and.returnValue(of(updatedUser));

        component.form.patchValue({ first_name: 'Updated' });
        component.onSubmit();

        expect(userServiceMock.updateProfile).toHaveBeenCalledWith(jasmine.objectContaining({
            first_name: 'Updated'
        }));
        expect(component.user).toEqual(updatedUser);
        expect(snackBarMock.open).toHaveBeenCalledWith('Profile updated successfully', 'Close', { duration: 3000 });
    });

    it('should reset form on cancel', () => {
        component.form.patchValue({ first_name: 'Changed' });
        component.onCancel();

        expect(userServiceMock.getProfile).toHaveBeenCalledTimes(2); // Once on init, once on cancel
        expect(component.form.value.first_name).toBe(mockUser.first_name);
    });
});
