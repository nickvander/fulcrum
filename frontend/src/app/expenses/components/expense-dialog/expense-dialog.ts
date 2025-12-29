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
import { Expense } from '../../../models/expense.model';

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
        MatButtonModule
    ],
    templateUrl: './expense-dialog.html',
    styleUrl: './expense-dialog.scss'
})
export class ExpenseDialogComponent implements OnInit {
    expenseForm: FormGroup;
    categories = ['Marketing', 'Software', 'Rent', 'Shipping', 'Office Supplies', 'Legal', 'Other'];
    currencies = ['USD', 'EUR', 'GBP', 'CAD', 'AUD'];

    constructor(
        private fb: FormBuilder,
        private dialogRef: MatDialogRef<ExpenseDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: { expense?: Expense }
    ) {
        this.expenseForm = this.fb.group({
            description: ['', Validators.required],
            amount: [0, [Validators.required, Validators.min(0.01)]],
            currency: ['USD', Validators.required],
            category: ['Other', Validators.required],
            date: [new Date(), Validators.required],
            product_id: [null],
            supplier_id: [null],
            purchase_order_id: [null]
        });
    }

    ngOnInit(): void {
        if (this.data.expense) {
            this.expenseForm.patchValue({
                ...this.data.expense,
                date: new Date(this.data.expense.date)
            });
        }
    }

    onSubmit(): void {
        if (this.expenseForm.valid) {
            const val = this.expenseForm.value;
            // Convert date to YYYY-MM-DD string for backend
            const date = val.date as Date;
            const formattedDate = date.toISOString().split('T')[0];

            this.dialogRef.close({
                ...val,
                date: formattedDate
            });
        }
    }

    onCancel(): void {
        this.dialogRef.close();
    }
}
