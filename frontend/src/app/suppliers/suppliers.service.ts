import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Supplier, SupplierCreate } from '../shared/models/supplier.model';
import { PurchaseOrder, PurchaseOrderCreate, PurchaseOrderStatus } from '../shared/models/purchase-order.model';

@Injectable({
  providedIn: 'root'
})
export class SuppliersService {
  private apiUrl = `${environment.apiUrl}`;

  constructor(private http: HttpClient) { }

  // --- Suppliers ---
  getSuppliers(skip: number = 0, limit: number = 100): Observable<Supplier[]> {
    let params = new HttpParams().set('skip', skip).set('limit', limit);
    return this.http.get<Supplier[]>(`${this.apiUrl}/suppliers/`, { params });
  }

  createSupplier(supplier: SupplierCreate): Observable<Supplier> {
    return this.http.post<Supplier>(`${this.apiUrl}/suppliers/`, supplier);
  }

  // --- Purchase Orders ---
  getPurchaseOrders(skip: number = 0, limit: number = 100): Observable<PurchaseOrder[]> {
    let params = new HttpParams().set('skip', skip).set('limit', limit);
    return this.http.get<PurchaseOrder[]>(`${this.apiUrl}/purchase-orders/`, { params });
  }

  getPurchaseOrder(id: number): Observable<PurchaseOrder> {
    return this.http.get<PurchaseOrder>(`${this.apiUrl}/purchase-orders/${id}`);
  }

  createPurchaseOrder(po: PurchaseOrderCreate): Observable<PurchaseOrder> {
    return this.http.post<PurchaseOrder>(`${this.apiUrl}/purchase-orders/`, po);
  }

  updatePurchaseOrderStatus(id: number, status: PurchaseOrderStatus): Observable<PurchaseOrder> {
    return this.http.post<PurchaseOrder>(`${this.apiUrl}/purchase-orders/${id}/status`, null, {
      params: { status }
    });
  }

  receivePurchaseOrderItems(id: number, items: { product_id: number, quantity: number }[]): Observable<PurchaseOrder> {
    return this.http.post<PurchaseOrder>(`${this.apiUrl}/purchase-orders/${id}/receive`, items);
  }
}
