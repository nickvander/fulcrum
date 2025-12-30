import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatIconModule } from '@angular/material/icon';
import { Expense } from '../../models/expense.model';

@Component({
    selector: 'app-expense-dialog',
    standalone: true,
    imports: [
        CommonModule,
        ReactiveFormsModule,
        MatDialogModule,
        MatFormFieldModule,
        MatInputModule,
        MatSelectModule,
        MatDatepickerModule,
        MatNativeDateModule,
        MatButtonModule,
        MatButtonToggleModule,
        MatIconModule
    ],
    templateUrl: './expense-dialog.html',
    styleUrl: './expense-dialog.scss'
})
export class ExpenseDialogComponent implements OnInit {
    expenseForm: FormGroup;
    categories: string[] = [];
    currencies = ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'MXN'];
    paymentMethods = [
        { value: 'cash', label: 'Cash' },
        { value: 'card', label: 'Credit/Debit Card' },
        { value: 'transfer', label: 'Bank Transfer' },
        { value: 'check', label: 'Check' }
    ];
    recurrenceIntervals = [
        { value: 'weekly', label: 'Weekly' },
        { value: 'monthly', label: 'Monthly' },
        { value: 'quarterly', label: 'Quarterly' },
        { value: 'yearly', label: 'Yearly' }
    ];
    showCustomCategory = false;
    isEditMode = false;

    constructor(
        private fb: FormBuilder,
        private dialogRef: MatDialogRef<ExpenseDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: { expense?: Expense; categories?: string[] }
    ) {
        this.categories = data.categories || [
            'Marketing', 'Software', 'Rent', 'Shipping', 'Office Supplies',
            'Legal', 'Gas/Transportation', 'Utilities', 'Packing Materials', 'Other'
        ];
        this.isEditMode = !!data.expense;

        this.expenseForm = this.fb.group({
            description: ['', Validators.required],
            amount: [0, [Validators.required, Validators.min(0.01)]],
            currency: ['USD', Validators.required],
            category: ['Other', Validators.required],
            customCategory: [''],
            is_custom_category: [false],
            date: [new Date(), Validators.required],
            expense_type: ['one_time', Validators.required],
            recurrence_interval: [null],
            reference_number: [''],
            payment_method: [null],
            notes: [''],
            product_id: [null],
            supplier_id: [null],
            purchase_order_id: [null]
        });
    }

    ngOnInit(): void {
        if (this.data.expense) {
            const expense = this.data.expense;
            this.expenseForm.patchValue({
                ...expense,
                date: new Date(expense.date)
            });

            // Check if category is custom
            if (expense.is_custom_category && !this.categories.includes(expense.category)) {
                this.showCustomCategory = true;
                this.expenseForm.patchValue({
                    category: '__custom__',
                    customCategory: expense.category
                });
            }
        }
    }

    onCategoryChange(value: string): void {
        this.showCustomCategory = value === '__custom__';
        if (!this.showCustomCategory) {
            this.expenseForm.patchValue({ customCategory: '', is_custom_category: false });
        } else {
            this.expenseForm.patchValue({ is_custom_category: true });
        }
    }

    onSubmit(): void {
        if (this.expenseForm.valid) {
            const val = this.expenseForm.value;

            // Handle custom category
            let category = val.category;
            let is_custom_category = val.is_custom_category;
            if (val.category === '__custom__' && val.customCategory) {
                category = val.customCategory;
                is_custom_category = true;
            }

            // Convert date to YYYY-MM-DD string for backend
            const date = val.date as Date;
            const formattedDate = date.toISOString().split('T')[0];

            // Build result object
            const result: any = {
                description: val.description,
                amount: val.amount,
                currency: val.currency,
                category: category,
                is_custom_category: is_custom_category,
                date: formattedDate,
                expense_type: val.expense_type,
                recurrence_interval: val.expense_type === 'recurring' ? val.recurrence_interval : null,
                reference_number: val.reference_number || null,
                payment_method: val.payment_method || null,
                notes: val.notes || null
            };

            this.dialogRef.close(result);
        }
    }

    onCancel(): void {
        this.dialogRef.close();
    }

    get isRecurring(): boolean {
        return this.expenseForm.get('expense_type')?.value === 'recurring';
    }
}
