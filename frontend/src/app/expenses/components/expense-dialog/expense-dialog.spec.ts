import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ExpenseDialogComponent } from './expense-dialog';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ExpenseService } from '../../services/expense.service';
import { of } from 'rxjs';

describe('ExpenseDialogComponent', () => {
    let component: ExpenseDialogComponent;
    let fixture: ComponentFixture<ExpenseDialogComponent>;
    let mockDialogRef: any;
    let mockExpenseService: any;

    beforeEach(async () => {
        mockDialogRef = {
            close: vi.fn()
        };

        mockExpenseService = {
            getReceipts: vi.fn().mockReturnValue(of([])),
            parseReceipt: vi.fn(),
            uploadReceipt: vi.fn(),
            deleteReceipt: vi.fn()
        };

        await TestBed.configureTestingModule({
            imports: [
                ExpenseDialogComponent, // Standalone
                TranslocoTestingModule.forRoot({ langs: { en: {}, 'es-MX': {} } }),
                NoopAnimationsModule,
                ReactiveFormsModule
            ],
            providers: [
                { provide: MatDialogRef, useValue: mockDialogRef },
                { provide: MAT_DIALOG_DATA, useValue: { expense: null, categories: [] } },
                { provide: ExpenseService, useValue: mockExpenseService },
                FormBuilder
            ]
        }).compileComponents();
    });

    beforeEach(() => {
        fixture = TestBed.createComponent(ExpenseDialogComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should initialize form', () => {
        expect(component.expenseForm).toBeDefined();
        expect(component.expenseForm.get('amount')).toBeTruthy();
    });
});
