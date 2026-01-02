import type { MockedObject } from "vitest";
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { RouterTestingModule } from '@angular/router/testing';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialogModule, MatDialog, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';

import { UserList } from './user-list';
import { UserService } from '../../services/user.service';
import { UserServiceMock } from '../../services/user.service.mock';
import { User } from '../../../shared/models/user.model';
import { AuthService } from '../../../core/services/auth.service';

import { Component } from '@angular/core';
import { UserBulkImportDialogComponent } from '../user-bulk-import-dialog/user-bulk-import-dialog';

@Component({
    selector: 'app-user-bulk-import-dialog',
    template: '',
    standalone: true
})
class MockUserBulkImportDialogComponent {
}

describe('UserList', () => {
    let component: UserList;
    let fixture: ComponentFixture<UserList>;
    let userService: UserService;
    let authService: MockedObject<AuthService>;
    let dialogSpy: MockedObject<MatDialog>;

    beforeEach(async () => {
        const authServiceSpy = {
            isAdmin: vi.fn().mockName("AuthService.isAdmin")
        } as unknown as MockedObject<AuthService>;
        const matDialogSpy = {
            open: vi.fn().mockName("MatDialog.open")
        } as unknown as MockedObject<MatDialog>;

        await TestBed.configureTestingModule({
            imports: [
                UserList,
                HttpClientTestingModule,
                ReactiveFormsModule,
                RouterTestingModule,
                MatSnackBarModule,
                MatSnackBarModule,
                MatDialogModule,
                MatFormFieldModule,
                MatFormFieldModule,
                MatInputModule,
                MatSelectModule,
                MatButtonModule,
                MatSlideToggleModule,
                MatIconModule,
                MatTooltipModule,
                NoopAnimationsModule,
                TranslocoTestingModule.forRoot({
                    langs: { en: {}, es: {} },
                    translocoConfig: { availableLangs: ['en', 'es'], defaultLang: 'en' }
                })
            ],
            providers: [
                { provide: UserService, useClass: UserServiceMock },
                { provide: AuthService, useValue: authServiceSpy },
                { provide: MatDialog, useValue: matDialogSpy }
            ]
        })
            .overrideComponent(UserList, {
                remove: { imports: [UserBulkImportDialogComponent] },
                add: { imports: [MockUserBulkImportDialogComponent] }
            })
            .compileComponents();

        userService = TestBed.inject(UserService);
        authService = TestBed.inject(AuthService) as MockedObject<AuthService>;
        dialogSpy = TestBed.inject(MatDialog) as MockedObject<MatDialog>;
    });

    beforeEach(() => {
        fixture = TestBed.createComponent(UserList);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should load users on initialization', () => {
        const mockUsers: User[] = [
            {
                id: 1,
                email: 'admin@test.com',
                employee_id: 'ADM123456',
                first_name: 'Admin',
                last_name: 'User',
                user_type: 'admin',
                is_active: true,
                is_superuser: true,
                force_password_change: false,
                avatar: 'https://example.com/admin-avatar.jpg',
                created_at: '2023-01-01T00:00:00Z',
                updated_at: '2023-01-01T00:00:00Z'
            },
            {
                id: 2,
                email: 'employee@test.com',
                employee_id: 'EMP789012',
                first_name: 'Employee',
                last_name: 'User',
                user_type: 'employee',
                is_active: true,
                is_superuser: false,
                force_password_change: false,
                avatar: null,
                created_at: '2023-01-01T00:00:00Z',
                updated_at: '2023-01-01T00:00:00Z'
            }
        ];

        vi.spyOn(userService, 'getUsers').mockReturnValue(of(mockUsers));

        component.loadUsers();

        expect(userService.getUsers).toHaveBeenCalled();
        expect(component.dataSource.data.length).toBe(2);
    });

    it('should apply filters correctly', () => {
        vi.spyOn(userService, 'getUsers').mockReturnValue(of([]));

        component.user_type_filter = 'admin';
        component.onFilterChange();

        expect(userService.getUsers).toHaveBeenCalledWith({ user_type: 'admin' });
    });

    it('should clear filters', () => {
        component.user_type_filter = 'admin';
        component.is_active_filter = 'true';
        component.search_filter = 'test';

        component.clearFilters();

        expect(component.user_type_filter).toBe('');
        expect(component.is_active_filter).toBe('');
        expect(component.search_filter).toBe('');
    });

    it('should deactivate user', () => {
        vi.spyOn(component, 'loadUsers');
        vi.spyOn(userService, 'deleteUser').mockReturnValue(of({ message: 'User deactivated' }));

        // Mock dialog ref to return true (confirmed)
        const dialogRefSpyObj = {
            afterClosed: vi.fn().mockReturnValue(of(true)),
            close: vi.fn().mockReturnValue(null)
        } as any;
        dialogSpy.open.mockReturnValue(dialogRefSpyObj as any);

        component.deactivateUser(1);

        expect(dialogSpy.open).toHaveBeenCalled();
        expect(userService.deleteUser).toHaveBeenCalledWith(1);
        expect(component.loadUsers).toHaveBeenCalled();
    });

    it('should permanently delete user', () => {
        vi.spyOn(component, 'loadUsers');
        vi.spyOn(userService, 'deleteUserPermanent').mockReturnValue(of({ message: 'User deleted' }));

        // Mock dialog ref to return true (confirmed)
        const dialogRefSpyObj = {
            afterClosed: vi.fn().mockReturnValue(of(true)),
            close: vi.fn().mockReturnValue(null)
        } as any;
        dialogSpy.open.mockReturnValue(dialogRefSpyObj as any);

        component.deleteUser(1);

        expect(dialogSpy.open).toHaveBeenCalled();
        expect(userService.deleteUserPermanent).toHaveBeenCalledWith(1);
        expect(component.loadUsers).toHaveBeenCalled();
    });
});
