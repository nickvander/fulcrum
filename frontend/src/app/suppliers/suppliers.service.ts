import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Supplier, SupplierCreate } from '../shared/models/supplier.model';
import { SupplierProductAlias } from '../shared/models/supplier-product.model';
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

  correctReceivedPurchaseOrderItems(
    id: number,
    items: { po_item_id?: number | null, product_id: number, variant_id?: number | null, quantity: number, reason?: string | null }[]
  ): Observable<PurchaseOrder> {
    return this.http.post<PurchaseOrder>(`${this.apiUrl}/purchase-orders/${id}/receive-correction`, items);
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

  getSupplierProductAliases(supplierId: number): Observable<SupplierProductAlias[]> {
    return this.http.get<SupplierProductAlias[]>(`${this.apiUrl}/supplier-products/aliases`, {
      params: { supplier_id: supplierId }
    });
  }

  deleteSupplierProductAlias(aliasId: number): Observable<SupplierProductAlias> {
    return this.http.delete<SupplierProductAlias>(`${this.apiUrl}/supplier-products/aliases/${aliasId}`);
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

  createImportReview(file: File, targetPoId?: number): Observable<SupplierDocumentImportReview> {
    const formData = new FormData();
    formData.append('file', file);
    let params = new HttpParams();
    if (targetPoId) {
      params = params.set('target_po_id', targetPoId.toString());
    }
    return this.http.post<SupplierDocumentImportReview>(`${this.apiUrl}/purchase-orders/imports/reviews`, formData, { params });
  }

  getImportReviews(status: string | null = 'pending'): Observable<SupplierDocumentImportReview[]> {
    let params = new HttpParams();
    if (status) {
      params = params.set('status', status);
    }
    return this.http.get<SupplierDocumentImportReview[]>(`${this.apiUrl}/purchase-orders/imports/reviews`, { params });
  }

  approveImportReview(reviewId: number, approval: SupplierDocumentImportApproveRequest): Observable<SupplierDocumentImportApproveResponse> {
    return this.http.post<SupplierDocumentImportApproveResponse>(
      `${this.apiUrl}/purchase-orders/imports/reviews/${reviewId}/approve`,
      approval
    );
  }

  rejectImportReview(reviewId: number): Observable<SupplierDocumentImportReview> {
    return this.http.post<SupplierDocumentImportReview>(`${this.apiUrl}/purchase-orders/imports/reviews/${reviewId}/reject`, {});
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
  matched_variant_id?: number | null;
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
  po_quantity_received?: number | null;
  po_remaining_quantity?: number | null;
  po_unit_cost: number | null;
  invoice_sku: string | null;
  invoice_description: string;
  invoice_quantity: number;
  invoice_unit_cost: number;
  invoice_line_total: number;
  receive_quantity?: number | null;
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
  matched_variant_id?: number | null;
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

export interface SupplierDocumentImportReview {
  id: number;
  file_name: string;
  content_type: string | null;
  source: string | null;
  status: 'pending' | 'approved' | 'rejected';
  mode: 'create' | 'match';
  supplier_id: number | null;
  purchase_order_id: number | null;
  extracted_data: DocumentParseResult;
  warnings: string[];
  created_at: string;
  reviewed_at: string | null;
}

export interface SupplierDocumentImportApproveRequest {
  supplier_id: number;
  currency: string;
  shipping_cost: number;
  tax_amount: number;
  notes?: string | null;
  items: ExtractedItem[];
}

export interface SupplierDocumentImportApproveResponse {
  import_review: SupplierDocumentImportReview;
  purchase_order: PurchaseOrder;
}
