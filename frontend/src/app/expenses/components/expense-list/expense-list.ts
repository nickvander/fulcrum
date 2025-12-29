import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { ExpenseService } from '../../services/expense.service';
import { Expense } from '../../../models/expense.model';
import { NotificationService } from '../../../core/services/notification.service';
import { ExpenseDialogComponent } from '../expense-dialog/expense-dialog';

@Component({
    selector: 'app-expense-list',
    standalone: true,
    imports: [
        CommonModule,
        MatTableModule,
        MatButtonModule,
        MatIconModule,
        MatCardModule,
        MatDialogModule
    ],
    templateUrl: './expense-list.html',
    styleUrl: './expense-list.scss'
})
export class ExpenseListComponent implements OnInit {
    expenses: Expense[] = [];
    displayedColumns: string[] = ['date', 'description', 'category', 'amount', 'actions'];

    constructor(
        private expenseService: ExpenseService,
        private notificationService: NotificationService,
        private dialog: MatDialog
    ) { }

    ngOnInit(): void {
        this.loadExpenses();
    }

    loadExpenses(): void {
        this.expenseService.getExpenses().subscribe({
            next: (data) => {
                this.expenses = data;
            },
            error: (error) => {
                console.error('Error loading expenses:', error);
                this.notificationService.showError('Error loading expenses');
            }
        });
    }

    onAddExpense(): void {
        const dialogRef = this.dialog.open(ExpenseDialogComponent, {
            width: '500px',
            data: {}
        });

        dialogRef.afterClosed().subscribe(result => {
            if (result) {
                this.expenseService.createExpense(result).subscribe({
                    next: () => {
                        this.notificationService.showSuccess('Expense added successfully');
                        this.loadExpenses();
                    },
                    error: (error) => {
                        console.error('Error adding expense:', error);
                        this.notificationService.showError('Error adding expense');
                    }
                });
            }
        });
    }

    onDeleteExpense(id: number): void {
        if (confirm('Are you sure you want to delete this expense?')) {
            this.expenseService.deleteExpense(id).subscribe({
                next: () => {
                    this.notificationService.showSuccess('Expense deleted');
                    this.loadExpenses();
                },
                error: (error) => {
                    console.error('Error deleting expense:', error);
                    this.notificationService.showError('Error deleting expense');
                }
            });
        }
    }
}
