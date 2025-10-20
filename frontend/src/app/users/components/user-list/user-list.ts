import { Component, OnInit, ViewChild, AfterViewInit } from '@angular/core';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { UserService, UserListParams } from '../../services/user.service';
import { User } from '../../models/user.model';
import { RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

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
  ],
})
export class UserList implements OnInit, AfterViewInit {
  displayedColumns: string[] = ['employee_id', 'first_name', 'last_name', 'email', 'user_type', 'is_active', 'is_superuser', 'actions'];
  dataSource: MatTableDataSource<User> = new MatTableDataSource();

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  // Filter properties
  user_type_filter: string = '';
  is_active_filter: string = '';
  search_filter: string = '';

  constructor(private userService: UserService) {}

  ngOnInit(): void {
    this.loadUsers();
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  loadUsers(): void {
    const params: UserListParams = {};
    
    if (this.user_type_filter) params.user_type = this.user_type_filter;
    if (this.is_active_filter) params.is_active = this.is_active_filter === 'true';
    if (this.search_filter) params.search = this.search_filter;

    this.userService.getUsers(params).subscribe((users) => {
      this.dataSource.data = users;
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

  deleteUser(id: number): void {
    if (confirm('Are you sure you want to delete this user?')) {
      this.userService.deleteUser(id).subscribe(() => {
        this.loadUsers(); // Refresh the list
      });
    }
  }
}
