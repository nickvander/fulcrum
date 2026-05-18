import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Expense, ExpenseSummary, ExpenseCreate, ExpenseUpdate, ExpenseReceipt, ReceiptParseResult } from '../models/expense.model';
import { environment } from '../../../environments/environment';

export interface ExpenseFilters {
    category?: string;
    expense_type?: string;
    start_date?: string;
    end_date?: string;
}

@Injectable({
    providedIn: 'root'
})
export class ExpenseService {
    private apiUrl = `${environment.apiUrl}/expenses`;

    constructor(private http: HttpClient) { }

    getExpenses(skip: number = 0, limit: number = 100, filters?: ExpenseFilters): Observable<Expense[]> {
        let params = new HttpParams()
            .set('skip', skip.toString())
            .set('limit', limit.toString());

        if (filters) {
            if (filters.category) params = params.set('category', filters.category);
            if (filters.expense_type) params = params.set('expense_type', filters.expense_type);
            if (filters.start_date) params = params.set('start_date', filters.start_date);
            if (filters.end_date) params = params.set('end_date', filters.end_date);
        }

        return this.http.get<Expense[]>(`${this.apiUrl}/`, { params });
    }

    getExpense(id: number): Observable<Expense> {
        return this.http.get<Expense>(`${this.apiUrl}/${id}`);
    }

    /** Download the expense list as CSV. Accepts the same filters as
     *  `getExpenses` so the export covers the same scope as the UI. */
    exportListCsv(filters?: ExpenseFilters, limit = 5000): Observable<Blob> {
        return this.http.get(`${this.apiUrl}/export`, {
            params: this.buildExportParams(filters, limit),
            responseType: 'blob',
        });
    }

    exportListPdf(filters?: ExpenseFilters, limit = 5000): Observable<Blob> {
        return this.http.get(`${this.apiUrl}/export-pdf`, {
            params: this.buildExportParams(filters, limit),
            responseType: 'blob',
        });
    }

    private buildExportParams(filters: ExpenseFilters | undefined, limit: number): HttpParams {
        let params = new HttpParams().set('limit', String(limit));
        if (filters?.category) params = params.set('category', filters.category);
        if (filters?.expense_type) params = params.set('expense_type', filters.expense_type);
        if (filters?.start_date) params = params.set('start_date', filters.start_date);
        if (filters?.end_date) params = params.set('end_date', filters.end_date);
        return params;
    }

    createExpense(expense: ExpenseCreate): Observable<Expense> {
        return this.http.post<Expense>(`${this.apiUrl}/`, expense);
    }

    updateExpense(id: number, expense: ExpenseUpdate): Observable<Expense> {
        return this.http.put<Expense>(`${this.apiUrl}/${id}`, expense);
    }

    deleteExpense(id: number): Observable<any> {
        return this.http.delete(`${this.apiUrl}/${id}`);
    }

    getSummary(startDate?: string, endDate?: string): Observable<ExpenseSummary> {
        let params = new HttpParams();
        if (startDate) params = params.set('start_date', startDate);
        if (endDate) params = params.set('end_date', endDate);
        return this.http.get<ExpenseSummary>(`${this.apiUrl}/summary`, { params });
    }

    getCategories(): Observable<string[]> {
        return this.http.get<string[]>(`${this.apiUrl}/categories`);
    }

    uploadReceipt(expenseId: number, file: File): Observable<ExpenseReceipt> {
        const formData = new FormData();
        formData.append('file', file);
        return this.http.post<ExpenseReceipt>(`${this.apiUrl}/${expenseId}/receipts`, formData);
    }

    getReceipts(expenseId: number): Observable<ExpenseReceipt[]> {
        return this.http.get<ExpenseReceipt[]>(`${this.apiUrl}/${expenseId}/receipts`);
    }

    deleteReceipt(receiptId: number): Observable<any> {
        return this.http.delete(`${this.apiUrl}/receipts/${receiptId}`);
    }

    parseReceipt(file: File): Observable<ReceiptParseResult> {
        const formData = new FormData();
        formData.append('file', file);
        return this.http.post<ReceiptParseResult>(`${this.apiUrl}/parse-receipt`, formData);
    }
}

