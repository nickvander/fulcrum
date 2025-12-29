import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Supplier, SupplierCreate } from '../shared/models/supplier.model';
import { PurchaseOrder, PurchaseOrderCreate, PurchaseOrderStatus } from '../shared/models/purchase-order.model';

export interface SupplierInvoice {
  id: number;
  po_id: number;
  invoice_number: string | null;
  invoice_date: string | null;
  file_path: string | null;
  created_at: string;
  updated_at: string;
}

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

  getSupplier(id: number): Observable<Supplier> {
    console.log(`[SuppliersService] Fetching supplier ${id} from ${this.apiUrl}/suppliers/${id}`);
    return this.http.get<Supplier>(`${this.apiUrl}/suppliers/${id}`);
  }

  createSupplier(supplier: SupplierCreate): Observable<Supplier> {
    return this.http.post<Supplier>(`${this.apiUrl}/suppliers/`, supplier);
  }

  getSupplierProducts(supplierId: number): Observable<import('../shared/models/supplier-product.model').SupplierProduct[]> {
    return this.http.get<import('../shared/models/supplier-product.model').SupplierProduct[]>(`${this.apiUrl}/suppliers/${supplierId}/products`);
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

  deletePurchaseOrder(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/purchase-orders/${id}`);
  }

  updatePurchaseOrderStatus(id: number, status: PurchaseOrderStatus): Observable<PurchaseOrder> {
    return this.http.post<PurchaseOrder>(`${this.apiUrl}/purchase-orders/${id}/status`, null, {
      params: { status }
    });
  }

  updatePurchaseOrder(id: number, po: Partial<PurchaseOrderCreate>): Observable<PurchaseOrder> {
    return this.http.put<PurchaseOrder>(`${this.apiUrl}/purchase-orders/${id}`, po);
  }

  receivePurchaseOrderItems(id: number, items: { product_id: number, quantity: number }[]): Observable<PurchaseOrder> {
    return this.http.post<PurchaseOrder>(`${this.apiUrl}/purchase-orders/${id}/receive`, items);
  }

  // --- Invoices ---
  getInvoices(poId: number): Observable<SupplierInvoice[]> {
    return this.http.get<SupplierInvoice[]>(`${this.apiUrl}/purchase-orders/${poId}/invoices`);
  }

  getCostAllocationPreview(poId: number, excludedItems: number[] = [], overrides: any = {}): Observable<any> {
    let params = new HttpParams();
    excludedItems.forEach(id => {
      params = params.append('excluded_items', id.toString());
    });
    if (overrides.shipping_cost !== undefined) params = params.append('shipping_cost', overrides.shipping_cost);
    if (overrides.tax_amount !== undefined) params = params.append('tax_amount', overrides.tax_amount);
    if (overrides.other_costs !== undefined) params = params.append('other_costs', overrides.other_costs);

    return this.http.get(`${this.apiUrl}/purchase-orders/${poId}/costs/preview`, { params });
  }

  applyCostAllocation(poId: number, excludedItems: number[] = []): Observable<any> {
    return this.http.post(`${this.apiUrl}/purchase-orders/${poId}/costs/apply`, {
      confirm: true,
      excluded_items: excludedItems
    });
  }

  uploadInvoice(poId: number, file: File, invoiceNumber?: string): Observable<SupplierInvoice> {
    const formData = new FormData();
    formData.append('file', file);
    if (invoiceNumber) {
      formData.append('invoice_number', invoiceNumber);
    }
    return this.http.post<SupplierInvoice>(`${this.apiUrl}/purchase-orders/${poId}/invoices`, formData);
  }

  deleteInvoice(invoiceId: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/purchase-orders/invoices/${invoiceId}`);
  }

  getInvoiceFileUrl(filePath: string): string {
    return `${this.apiUrl.replace('/api/v1', '')}/${filePath}`;
  }
}

