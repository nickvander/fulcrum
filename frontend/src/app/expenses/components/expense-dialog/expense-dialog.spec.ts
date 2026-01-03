import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ExpenseDialogComponent } from './expense-dialog';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientTestingModule } from '@angular/common/http/testing';

describe('ExpenseDialogComponent', () => {
    let component: ExpenseDialogComponent;
    let fixture: ComponentFixture<ExpenseDialogComponent>;
    let mockDialogRef: any;

    beforeEach(async () => {
        mockDialogRef = {
            close: vi.fn()
        };

        await TestBed.configureTestingModule({
            imports: [
                ExpenseDialogComponent, // Standalone
                TranslocoTestingModule.forRoot({ langs: { en: {}, 'es-MX': {} } }),
                NoopAnimationsModule,
                HttpClientTestingModule,
                ReactiveFormsModule
            ],
            providers: [
                { provide: MatDialogRef, useValue: mockDialogRef },
                { provide: MAT_DIALOG_DATA, useValue: { expense: null, categories: [] } },
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
