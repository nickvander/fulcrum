import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';

import { AuditLogList } from './audit-log-list';
import { AuditLogService } from '../../services/audit-log.service';
import { UserService } from '../../services/user.service';
import { UserServiceMock } from '../../services/user.service.mock';
import { UserAuditLog } from '../../models/audit-log.model';
import { User } from '../../../shared/models/user.model';

describe('AuditLogList', () => {
    let component: AuditLogList;
    let fixture: ComponentFixture<AuditLogList>;
    let auditLogService: jasmine.SpyObj<AuditLogService>;
    let userService: UserService;

    const mockAuditLogs: UserAuditLog[] = [
        {
            id: 1,
            user_id: 1,
            action_performed_by: 2,
            action: 'UPDATE',
            details: 'Updated profile',
            ip_address: '127.0.0.1',
            created_at: '2023-01-01T00:00:00Z'
        },
        {
            id: 2,
            user_id: 2,
            action_performed_by: 1,
            action: 'DELETE',
            details: 'Deleted user',
            ip_address: '127.0.0.1',
            created_at: '2023-01-02T00:00:00Z'
        }
    ];

    const mockUsers: User[] = [
        {
            id: 1,
            email: 'user1@example.com',
            first_name: 'User',
            last_name: 'One',
            user_type: 'employee',
            is_active: true,
            is_superuser: false,
            force_password_change: false,
            employee_id: 'EMP001',
            avatar: null,
            created_at: '2023-01-01T00:00:00Z',
            updated_at: '2023-01-01T00:00:00Z'
        },
        {
            id: 2,
            email: 'user2@example.com',
            first_name: 'User',
            last_name: 'Two',
            user_type: 'admin',
            is_active: true,
            is_superuser: true,
            force_password_change: false,
            employee_id: 'EMP002',
            avatar: null,
            created_at: '2023-01-01T00:00:00Z',
            updated_at: '2023-01-01T00:00:00Z'
        }
    ];

    beforeEach(async () => {
        const auditLogServiceSpy = jasmine.createSpyObj('AuditLogService', ['getAuditLogs']);
        auditLogServiceSpy.getAuditLogs.and.returnValue(of(mockAuditLogs));

        await TestBed.configureTestingModule({
            imports: [
                AuditLogList,
                HttpClientTestingModule,
                FormsModule,
                MatTableModule,
                MatPaginatorModule,
                MatSortModule,
                MatFormFieldModule,
                MatInputModule,
                MatSelectModule,
                MatButtonModule,
                BrowserAnimationsModule
            ],
            providers: [
                { provide: AuditLogService, useValue: auditLogServiceSpy },
                { provide: UserService, useClass: UserServiceMock }
            ]
        })
            .compileComponents();

        auditLogService = TestBed.inject(AuditLogService) as jasmine.SpyObj<AuditLogService>;
        userService = TestBed.inject(UserService);

        // Mock getUser to return specific users
        spyOn(userService, 'getUser').and.callFake((id) => {
            const user = mockUsers.find(u => u.id === id);
            return of(user || mockUsers[0]);
        });

        // Mock getUsers to return all users
        spyOn(userService, 'getUsers').and.returnValue(of(mockUsers));
    });

    beforeEach(() => {
        fixture = TestBed.createComponent(AuditLogList);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should load users on init', () => {
        expect(userService.getUsers).toHaveBeenCalled();
        expect(component.users.length).toBe(2);
    });

    it('should load audit logs on init', () => {
        expect(auditLogService.getAuditLogs).toHaveBeenCalled();
        expect(component.dataSource.data.length).toBe(2);
    });

    it('should enhance audit logs with user details', () => {
        // Wait for async operations to complete
        fixture.detectChanges();

        const logs = component.dataSource.data;
        expect(logs[0].user_email).toBe('user1@example.com');
        expect(logs[0].actor_email).toBe('user2@example.com');

        expect(logs[1].user_email).toBe('user2@example.com');
        expect(logs[1].actor_email).toBe('user1@example.com');
    });

    it('should filter logs when filter changes', () => {
        component.user_filter = 1;
        component.action_filter = 'UPDATE';

        component.onFilterChange();

        expect(auditLogService.getAuditLogs).toHaveBeenCalledWith({
            user_id: 1,
            action: 'UPDATE'
        });
    });

    it('should clear filters', () => {
        component.user_filter = 1;
        component.action_filter = 'UPDATE';

        component.clearFilters();

        expect(component.user_filter).toBeNull();
        expect(component.action_filter).toBe('');
        expect(auditLogService.getAuditLogs).toHaveBeenCalled();
    });
});
