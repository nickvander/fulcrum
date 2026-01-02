import { Component, OnInit, OnDestroy, ViewChild, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatMenuModule } from '@angular/material/menu';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator'; // Added Paginator
import { Subject, takeUntil } from 'rxjs';
import { ExpenseService, ExpenseFilters } from '../../services/expense.service';
import { Expense, ExpenseSummary } from '../../models/expense.model';
import { NotificationService } from '../../../core/services/notification.service';
import { ExpenseDialogComponent } from '../expense-dialog/expense-dialog';
import { StatCardComponent } from '../../../dashboard/widgets/stat-card/stat-card.component';
import { DateRangePresetsComponent } from '../../../shared/components/date-range-presets/date-range-presets.component';
import { DateRangeService, DateRange } from '../../../shared/services/date-range.service';
import { ConfirmationDialog, ConfirmationDialogData } from '../../../shared/components/confirmation-dialog/confirmation-dialog';
import { TranslocoModule } from '@ngneat/transloco';

@Component({
    selector: 'app-expense-list',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        MatTableModule,
        MatSortModule,
        MatButtonModule,
        MatIconModule,
        MatCardModule,
        MatDialogModule,
        MatFormFieldModule,
        MatSelectModule,
        MatInputModule,
        MatProgressBarModule,
        MatChipsModule,
        MatTooltipModule,
        MatMenuModule,
        MatPaginatorModule,
        StatCardComponent,
        DateRangePresetsComponent,
        TranslocoModule
    ],
    templateUrl: './expense-list.html',
    styleUrl: './expense-list.scss'
})
export class ExpenseListComponent implements OnInit, OnDestroy, AfterViewInit {
    allExpenses: Expense[] = [];  // All expenses loaded once
    dataSource = new MatTableDataSource<Expense>([]);
    @ViewChild(MatSort) sort!: MatSort;
    @ViewChild(MatPaginator) paginator!: MatPaginator; // Added ViewChild

    expenses: Expense[] = [];      // Filtered expenses for display
    summary: ExpenseSummary | null = null;
    categories: string[] = [];
    displayedColumns: string[] = ['date', 'description', 'category', 'type', 'amount', 'actions'];

    // Filters
    selectedCategory: string = '';
    selectedType: string = '';
    startDate: Date | null = null;
    endDate: Date | null = null;

    // Loading state
    isLoading = false;

    private destroy$ = new Subject<void>();

    constructor(
        private expenseService: ExpenseService,
        private notificationService: NotificationService,
        private dialog: MatDialog,
        private router: Router,
        private dateRangeService: DateRangeService
    ) { }

    ngOnInit(): void {
        // Initialize date range from service's current value
        const currentRange = this.dateRangeService.currentRange;
        this.startDate = currentRange.startDate;
        this.endDate = currentRange.endDate;

        this.loadCategories();
        this.loadAllExpenses();  // Load once

        // Subscribe to future global date range changes (client-side filter only)
        this.dateRangeService.dateRange$
            .pipe(takeUntil(this.destroy$))
            .subscribe(range => {
                this.startDate = range.startDate;
                this.endDate = range.endDate;
                this.applyFilters();  // No API call, just filter
            });
    }

    ngAfterViewInit() {
        this.dataSource.paginator = this.paginator;
        this.dataSource.sort = this.sort;
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }

    loadCategories(): void {
        this.expenseService.getCategories().subscribe({
            next: (cats) => this.categories = cats,
            error: () => this.categories = ['Marketing', 'Software', 'Rent', 'Other']
        });
    }

    /** Load all expenses once (no filters) */
    loadAllExpenses(): void {
        this.isLoading = true;
        this.expenseService.getExpenses(0, 500).subscribe({  // Load more to cover all
            next: (data) => {
                this.allExpenses = data;
                this.applyFilters();
                this.calculateSummary();
                this.isLoading = false;
            },
            error: (error) => {
                console.error('Error loading expenses:', error);
                this.notificationService.showError('Error loading expenses');
                this.isLoading = false;
            }
        });
    }

    /** Apply filters client-side for instant response */
    applyFilters(): void {
        let filtered = [...this.allExpenses];

        // Category filter
        if (this.selectedCategory) {
            filtered = filtered.filter(e => e.category === this.selectedCategory);
        }

        // Type filter
        if (this.selectedType) {
            filtered = filtered.filter(e => e.expense_type === this.selectedType);
        }

        // Date range filter
        if (this.startDate && this.endDate) {
            const startStr = this.formatDate(this.startDate);
            const endStr = this.formatDate(this.endDate);
            filtered = filtered.filter(e => {
                const expDate = e.date;  // Already in YYYY-MM-DD format
                return expDate && expDate >= startStr && expDate <= endStr;
            });
        }

        this.expenses = filtered;
        this.dataSource.data = filtered;
        this.dataSource.sort = this.sort;
        this.dataSource.paginator = this.paginator; // Re-link paginator
    }

    /** Calculate summary from filtered expenses */
    calculateSummary(): void {
        const total = this.expenses.reduce((sum, e) => sum + e.amount, 0);
        const byCategory: { [key: string]: number } = {};
        this.expenses.forEach(e => {
            byCategory[e.category] = (byCategory[e.category] || 0) + e.amount;
        });
        this.summary = {
            total_amount: total,
            count: this.expenses.length,
            by_category: byCategory,
            by_type: { one_time: 0, recurring: 0 },
            by_user: {},
            unreimbursed_total: 0
        };
    }

    loadSummary(): void {
        const startDate = this.startDate ? this.formatDate(this.startDate) : undefined;
        const endDate = this.endDate ? this.formatDate(this.endDate) : undefined;

        this.expenseService.getSummary(startDate, endDate).subscribe({
            next: (summary) => this.summary = summary,
            error: () => this.summary = null
        });
    }

    formatDate(date: Date): string {
        return date.toISOString().split('T')[0];
    }

    onFilterChange(): void {
        this.applyFilters();  // Client-side filter only
    }

    onDateRangeChange(range: DateRange | null): void {
        this.startDate = range?.startDate || null;
        this.endDate = range?.endDate || null;
        this.onFilterChange();
    }

    clearFilters(): void {
        this.selectedCategory = '';
        this.selectedType = '';
        this.dateRangeService.setPreset('week');  // Reset to default
        this.applyFilters();
    }

    hasActiveFilters(): boolean {
        return !!(this.selectedCategory || this.selectedType);
    }

    onCreateSupplier(): void {
        this.router.navigate(['/suppliers/id/new']);
    }

    onAddExpense(): void {
        const dialogRef = this.dialog.open(ExpenseDialogComponent, {
            width: '600px',
            maxHeight: '90vh',
            data: { categories: this.categories }
        });

        dialogRef.afterClosed().subscribe(result => {
            if (result) {
                this.expenseService.createExpense(result).subscribe({
                    next: () => {
                        this.notificationService.showSuccess('Expense added successfully');
                        this.loadAllExpenses();
                    },
                    error: (error) => {
                        console.error('Error adding expense:', error);
                        this.notificationService.showError('Error adding expense');
                    }
                });
            }
        });
    }

    onEditExpense(expense: Expense): void {
        const dialogRef = this.dialog.open(ExpenseDialogComponent, {
            width: '600px',
            maxHeight: '90vh',
            data: { expense, categories: this.categories }
        });

        dialogRef.afterClosed().subscribe(result => {
            if (result) {
                this.expenseService.updateExpense(expense.id, result).subscribe({
                    next: () => {
                        this.notificationService.showSuccess('Expense updated');
                        this.loadAllExpenses();
                    },
                    error: (error) => {
                        console.error('Error updating expense:', error);
                        this.notificationService.showError('Error updating expense');
                    }
                });
            }
        });
    }

    onDeleteExpense(id: number): void {
        const dialogRef = this.dialog.open(ConfirmationDialog, {
            data: {
                title: 'Delete Expense',
                message: 'Are you sure you want to delete this expense?'
            } as ConfirmationDialogData
        });

        dialogRef.afterClosed().subscribe(confirmed => {
            if (confirmed) {
                this.expenseService.deleteExpense(id).subscribe({
                    next: () => {
                        this.notificationService.showSuccess('Expense deleted');
                        this.loadAllExpenses();
                    },
                    error: (error) => {
                        console.error('Error deleting expense:', error);
                        this.notificationService.showError('Error deleting expense');
                    }
                });
            }
        });
    }

    getTypeIcon(type: string): string {
        return type === 'recurring' ? 'repeat' : 'event';
    }

    getTypeLabel(type: string): string {
        return type === 'recurring' ? 'Recurring' : 'One-time';
    }

    getCategoryColor(category: string): string {
        const colors: { [key: string]: string } = {
            'Marketing': '#e91e63',
            'Software': '#9c27b0',
            'Rent': '#3f51b5',
            'Shipping': '#03a9f4',
            'Office Supplies': '#009688',
            'Legal': '#ff5722',
            'Gas/Transportation': '#795548',
            'Utilities': '#607d8b',
            'Packing Materials': '#4caf50',
            'Other': '#9e9e9e'
        };
        return colors[category] || '#9e9e9e';
    }

    getTotalExpenses(): string {
        return this.summary?.total_amount?.toFixed(2) || '0.00';
    }

    getRecurringTotal(): string {
        return this.summary?.by_type?.recurring?.toFixed(2) || '0.00';
    }

    getOneTimeTotal(): string {
        return this.summary?.by_type?.one_time?.toFixed(2) || '0.00';
    }
}
