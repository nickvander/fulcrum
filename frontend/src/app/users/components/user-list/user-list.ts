import { Component, OnInit, ViewChild, AfterViewInit } from '@angular/core';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatDialog } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { UserService, UserListParams } from '../../services/user.service';
import { User } from '../../models/user.model';
import { RouterModule, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ConfirmationDialog } from '../confirmation-dialog/confirmation-dialog';
import { PasswordResetDialog } from '../password-reset-dialog/password-reset-dialog';
import { UserCreateModal } from '../user-create-modal/user-create-modal';

@Component({
  selector: 'app-user-list',
  templateUrl: './user-list.html',
  styleUrls: ['./user-list.scss'],
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatIconModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatTooltipModule,
    MatProgressBarModule,
  ],
})
export class UserList implements OnInit, AfterViewInit {
  displayedColumns: string[] = ['avatar', 'employee_id', 'first_name', 'last_name', 'email', 'user_type', 'is_active', 'actions'];
  dataSource: MatTableDataSource<User> = new MatTableDataSource();
  isLoading = false;

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  // Filter properties
  user_type_filter: string = '';
  is_active_filter: string = '';
  search_filter: string = '';

  constructor(
    private userService: UserService, 
    private dialog: MatDialog,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadUsers();
  }

  avatarError(event: any): void {
    event.target.src = 'assets/images/default-avatar.png';
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  loadUsers(): void {
    this.isLoading = true;
    const params: UserListParams = {};
    
    if (this.user_type_filter) params.user_type = this.user_type_filter;
    if (this.is_active_filter) params.is_active = this.is_active_filter === 'true';
    if (this.search_filter) params.search = this.search_filter;

    this.userService.getUsers(params).subscribe({
      next: (users) => {
        this.dataSource.data = users;
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading users:', error);
        this.isLoading = false;
      }
    });
  }

  onFilterChange(): void {
    this.loadUsers();
  }

  clearFilters(): void {
    this.user_type_filter = '';
    this.is_active_filter = '';
    this.search_filter = '';
    this.loadUsers();
  }

  addNewUser(): void {
    const dialogRef = this.dialog.open(UserCreateModal, {
      width: '500px',
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        // User was created successfully, refresh the list
        this.loadUsers();
      }
    });
  }

  viewAuditLogs(): void {
    // Navigate to the audit logs page
    this.router.navigate(['/users/audit-logs']);
  }

  deactivateUser(id: number): void {
    const dialogRef = this.dialog.open(ConfirmationDialog, {
      width: '400px',
      data: {
        title: 'Deactivate User',
        message: 'Are you sure you want to deactivate this user? The user will no longer be able to log in.',
        confirmText: 'Deactivate',
        cancelText: 'Cancel'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.userService.deleteUser(id).subscribe({
          next: () => {
            this.loadUsers(); // Refresh the list
          },
          error: (error) => {
            console.error('Error deactivating user:', error);
          }
        });
      }
    });
  }

  deleteUser(id: number): void {
    const dialogRef = this.dialog.open(ConfirmationDialog, {
      width: '400px',
      data: {
        title: 'Permanently Delete User',
        message: 'Are you sure you want to permanently delete this user? This action cannot be undone.',
        confirmText: 'Delete Permanently',
        cancelText: 'Cancel'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        // Call the permanent delete endpoint
        this.userService.deleteUserPermanent(id).subscribe({
          next: () => {
            this.loadUsers(); // Refresh the list
          },
          error: (error) => {
            console.error('Error permanently deleting user:', error);
          }
        });
      }
    });
  }

  resetUserPassword(id: number, email: string): void {
    const dialogRef = this.dialog.open(PasswordResetDialog, {
      width: '400px',
      data: {
        userId: id,
        email: email,
        isForAdmin: true
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        // Password reset was successful, no need to refresh the user list
        // The password reset doesn't change any user properties visible in the list
      }
    });
  }
}
