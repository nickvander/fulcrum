import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginator, MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatButtonModule } from '@angular/material/button';
import { AuditLogService, AuditLog } from '../../services/audit-log.service';

@Component({
  selector: 'app-audit-logs',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatTableModule,
    MatPaginatorModule,
    MatInputModule,
    MatFormFieldModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatButtonModule
  ],
  templateUrl: './audit-logs.component.html',
  styleUrls: ['./audit-logs.component.scss']
})
export class AuditLogsComponent implements OnInit {
  displayedColumns: string[] = ['id', 'action', 'user', 'actor', 'details', 'created_at'];
  dataSource = new MatTableDataSource<AuditLog>([]);
  resultsLength = 0;
  pageSize = 20;
  pageIndex = 0;

  filterAction = '';
  filterUserId: number | undefined;
  filterStartDate: Date | undefined;
  filterEndDate: Date | undefined;

  @ViewChild(MatPaginator) paginator!: MatPaginator;

  constructor(private auditLogService: AuditLogService) { }

  ngOnInit(): void {
    this.loadLogs();
  }

  loadLogs(): void {
    const filters: any = {};
    if (this.filterAction) filters.action = this.filterAction;
    if (this.filterUserId) filters.userId = this.filterUserId;
    if (this.filterStartDate) filters.startDate = this.filterStartDate.toISOString();
    if (this.filterEndDate) filters.endDate = this.filterEndDate.toISOString();

    this.auditLogService.getAuditLogs(this.pageIndex, this.pageSize, filters)
      .subscribe(data => {
        this.dataSource.data = data;
        // Note: Backend pagination total count is not yet implemented in the API response wrapper, 
        // assuming simple list for now. For full pagination we'd need the API to return { items: [], total: number }
        // For now, we'll just show what we got.
        this.resultsLength = 100; // Placeholder until backend supports count
      });
  }

  onPageChange(event: PageEvent): void {
    this.pageIndex = event.pageIndex;
    this.pageSize = event.pageSize;
    this.loadLogs();
  }
}
