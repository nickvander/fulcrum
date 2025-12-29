import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Expense, ExpenseCreate, ExpenseUpdate } from '../../models/expense.model';
import { environment } from '../../../environments/environment';

@Injectable({
    providedIn: 'root'
})
export class ExpenseService {
    private apiUrl = `${environment.apiUrl}/v1/expenses`;

    constructor(private http: HttpClient) { }

    getExpenses(skip: number = 0, limit: number = 100): Observable<Expense[]> {
        return this.http.get<Expense[]>(`${this.apiUrl}/`, {
            params: { skip: skip.toString(), limit: limit.toString() }
        });
    }

    getExpense(id: number): Observable<Expense> {
        return this.http.get<Expense>(`${this.apiUrl}/${id}`);
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
}
