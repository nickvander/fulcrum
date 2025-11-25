import { Component, OnInit, ViewChild } from '@angular/core';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { AuditLogService } from '../../services/audit-log.service';
import { UserAuditLog } from '../../models/audit-log.model';
import { UserService } from '../../services/user.service';
import { User } from '../../models/user.model';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable, forkJoin } from 'rxjs';

@Component({
  selector: 'app-audit-log-list',
  templateUrl: './audit-log-list.html',
  styleUrls: ['./audit-log-list.scss'],
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
  ],
})
export class AuditLogList implements OnInit {
  displayedColumns: string[] = ['timestamp', 'user', 'actor', 'action', 'details', 'ip_address'];
  dataSource: MatTableDataSource<UserAuditLog> = new MatTableDataSource();

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  // Filter properties
  user_filter: number | null = null;
  action_filter: string = '';
  users: User[] = [];

  constructor(
    private auditLogService: AuditLogService,
    private userService: UserService
  ) { }

  ngOnInit(): void {
    this.loadUsers();
    this.loadAuditLogs();
  }

  loadUsers(): void {
    this.userService.getUsers().subscribe(users => {
      this.users = users;
    });
  }

  loadAuditLogs(): void {
    const params: any = {};

    if (this.user_filter) params.user_id = this.user_filter;
    if (this.action_filter) params.action = this.action_filter;

    this.auditLogService.getAuditLogs(params).subscribe(auditLogs => {
      // Enhance audit logs with user/actor emails for display
      this.enhanceAuditLogsWithUserDetails(auditLogs);
      this.dataSource.data = auditLogs;
    });
  }

  enhanceAuditLogsWithUserDetails(auditLogs: UserAuditLog[]): void {
    // Create a unique set of user IDs that need to be resolved
    const userIds = new Set<number>();
    const actorIds = new Set<number>();

    auditLogs.forEach(log => {
      userIds.add(log.user_id);
      actorIds.add(log.action_performed_by);
    });

    const userIdsArray = Array.from(userIds);
    const actorIdsArray = Array.from(actorIds);

    // Fetch user details for both affected users and actors
    const userRequests = userIdsArray.map(id => this.userService.getUser(id));
    const actorRequests = actorIdsArray.map(id => this.userService.getUser(id));

    forkJoin([...userRequests, ...actorRequests]).subscribe(results => {
      // Create mapping of user ID to email
      const userMap: { [key: number]: string } = {};

      // Process users first (results from userRequests)
      results.slice(0, userRequests.length).forEach((user, index) => {
        userMap[userIdsArray[index]] = user.email;
      });

      // Process actors next (results from actorRequests)
      results.slice(userRequests.length).forEach((user, index) => {
        userMap[actorIdsArray[index]] = user.email;
      });

      // Update audit logs with user/actor emails
      auditLogs.forEach(log => {
        log.user_email = userMap[log.user_id] || 'Unknown';
        log.actor_email = userMap[log.action_performed_by] || 'System';
      });

      // Update the data source
      this.dataSource.data = [...auditLogs];
    });
  }

  onFilterChange(): void {
    this.loadAuditLogs();
  }

  clearFilters(): void {
    this.user_filter = null;
    this.action_filter = '';
    this.loadAuditLogs();
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }
}