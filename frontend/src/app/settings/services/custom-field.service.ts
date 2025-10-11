import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { CustomField } from '../models/custom-field.model';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class CustomFieldService {
  private apiUrl = `${environment.apiUrl}/custom-fields`;

  private readonly _customFields = new BehaviorSubject<CustomField[]>([]);
  readonly customFields$ = this._customFields.asObservable();

  constructor(private http: HttpClient) {}

  getCustomFields(): Observable<CustomField[]> {
    return this.http.get<CustomField[]>(this.apiUrl).pipe(
      tap(customFields => {
        this._customFields.next(customFields);
      })
    );
  }

  createCustomField(customField: Omit<CustomField, 'id'>): Observable<CustomField> {
    return this.http.post<CustomField>(this.apiUrl, customField).pipe(
      tap(() => this.getCustomFields().subscribe())
    );
  }

  updateCustomField(customField: CustomField): Observable<CustomField> {
    return this.http.put<CustomField>(`${this.apiUrl}/${customField.id}`, customField).pipe(
      tap(() => this.getCustomFields().subscribe())
    );
  }

  deleteCustomField(id: number): Observable<unknown> {
    return this.http.delete(`${this.apiUrl}/${id}`).pipe(
      tap(() => this.getCustomFields().subscribe())
    );
  }
}
