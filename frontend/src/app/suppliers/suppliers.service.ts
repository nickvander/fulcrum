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
  parsed_data?: string | null;
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

  getSuppliersForProduct(productId: number): Observable<import('../shared/models/supplier-product.model').SupplierProduct[]> {
    return this.http.get<import('../shared/models/supplier-product.model').SupplierProduct[]>(`${this.apiUrl}/supplier-products/by-product/${productId}`);
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

  receivePurchaseOrderItems(
    id: number,
    items: { po_item_id?: number | null, product_id: number, variant_id?: number | null, quantity: number }[]
  ): Observable<PurchaseOrder> {
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

  parseAndMatchInvoice(poId: number, file: File): Observable<InvoiceMatchResult> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<InvoiceMatchResult>(`${this.apiUrl}/purchase-orders/${poId}/invoices/parse-and-match`, formData);
  }

  // --- PO Ingestion (Unified) ---
  parseDocument(file: File, targetPoId?: number): Observable<DocumentParseResult> {
    const formData = new FormData();
    formData.append('file', file);
    let params = new HttpParams();
    if (targetPoId) {
      params = params.set('target_po_id', targetPoId.toString());
    }
    return this.http.post<DocumentParseResult>(`${this.apiUrl}/purchase-orders/parse-document`, formData, { params });
  }

  /** @deprecated Use parseDocument instead */
  ingestPurchaseOrder(file: File, useAi: boolean = false): Observable<PoIngestionResponse> {
    const formData = new FormData();
    formData.append('file', file);
    let params = new HttpParams();
    if (useAi) {
      params = params.set('use_ai', 'true');
    }
    return this.http.post<PoIngestionResponse>(`${this.apiUrl}/purchase-orders/ingest`, formData, { params });
  }
}

// PO Ingestion Response Types
export interface ExtractedLineItem {
  sku: string | null;
  description: string;
  quantity: number;
  unit_cost: number;
  line_total: number;
  matched_product_id?: number | null;
}

export interface PoIngestionResponse {
  supplier_name: string | null;
  po_number: string | null;
  po_date: string | null;
  currency: string;
  payment_terms: string | null;
  items: ExtractedLineItem[];
  subtotal: number;
  shipping_cost: number;
  tax_amount: number;
  total_amount: number;
  extraction_method: string;
  confidence_score: number;
  warnings: string[];
}

// Invoice Parse & Match Types
export interface InvoiceMatchItem {
  po_item_id: number | null;
  po_description: string | null;
  po_quantity: number | null;
  po_unit_cost: number | null;
  invoice_sku: string | null;
  invoice_description: string;
  invoice_quantity: number;
  invoice_unit_cost: number;
  invoice_line_total: number;
  match_status: 'matched' | 'quantity_diff' | 'price_diff' | 'quantity_price_diff' | 'unmatched';
  confidence: number;
  discrepancy_details: string | null;
}

export interface InvoiceMatchResult {
  invoice_number: string | null;
  invoice_date: string | null;
  vendor_name: string | null;
  matches: InvoiceMatchItem[];
  unmatched_po_items: any[];
  unmatched_invoice_items: any[];
  total_discrepancy: number;
  overall_confidence: number;
  extraction_confidence: number;
}

// Unified Document Parse Types
export interface ExtractedItem {
  sku: string | null;
  description: string;
  quantity: number;
  unit_cost: number;
  line_total: number;
  matched_product_id?: number | null;
}

export interface DocumentParseResult {
  mode: 'create' | 'match';

  // Extracted document data
  vendor_name: string | null;
  po_number: string | null;
  invoice_number: string | null;
  document_date: string | null;
  currency: string;
  items: ExtractedItem[];
  subtotal: number;
  shipping_cost: number;
  tax_amount: number;
  total_amount: number;
  confidence: number;

  // If mode == "match"
  matched_po_id: number | null;
  matched_po_number: string | null;
  matched_supplier_name: string | null;
  match_confidence: number;
  matches: InvoiceMatchItem[];
  unmatched_po_items: any[];
  unmatched_invoice_items: any[];
  total_discrepancy: number;
}
