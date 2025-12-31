import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface ApiKeyInfo {
    id: number;
    name: string;
    key_prefix: string;
    is_active: boolean;
    last_used_at: string | null;
    created_at: string;
}

export interface ApiKeyCreateResponse {
    id: number;
    name: string;
    key_prefix: string;
    api_key: string;  // Full key - only returned at creation!
    created_at: string;
}

export interface ExportOptions {
    format: 'csv' | 'json';
}

@Injectable({
    providedIn: 'root'
})
export class IntegrationsService {
    private apiUrl = `${environment.apiUrl}/integrations`;

    constructor(private http: HttpClient) { }

    // ==========================================================================
    // API Keys
    // ==========================================================================

    getApiKeys(): Observable<ApiKeyInfo[]> {
        return this.http.get<ApiKeyInfo[]>(`${this.apiUrl}/api-keys`);
    }

    createApiKey(name: string): Observable<ApiKeyCreateResponse> {
        return this.http.post<ApiKeyCreateResponse>(`${this.apiUrl}/api-keys`, { name });
    }

    revokeApiKey(keyId: number): Observable<{ message: string }> {
        return this.http.delete<{ message: string }>(`${this.apiUrl}/api-keys/${keyId}`);
    }

    // ==========================================================================
    // Data Export
    // ==========================================================================

    /**
     * Generic export method for any entity
     */
    exportEntity(entity: string, format: 'csv' | 'json' = 'csv'): Observable<Blob> {
        return this.http.get(`${this.apiUrl}/export/${entity}`, {
            params: { format },
            responseType: 'blob'
        });
    }

    exportProducts(format: 'csv' | 'json' = 'csv'): Observable<Blob> {
        return this.exportEntity('products', format);
    }

    exportSuppliers(format: 'csv' | 'json' = 'csv'): Observable<Blob> {
        return this.exportEntity('suppliers', format);
    }

    exportInventory(format: 'csv' | 'json' = 'csv'): Observable<Blob> {
        return this.exportEntity('inventory', format);
    }

    exportPurchaseOrders(format: 'csv' | 'json' = 'csv'): Observable<Blob> {
        return this.exportEntity('purchase-orders', format);
    }

    exportExpenses(format: 'csv' | 'json' = 'csv'): Observable<Blob> {
        return this.exportEntity('expenses', format);
    }

    exportCampaigns(format: 'csv' | 'json' = 'csv'): Observable<Blob> {
        return this.exportEntity('campaigns', format);
    }

    /**
     * Helper to download a blob as a file
     */
    downloadBlob(blob: Blob, filename: string): void {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }

    // ==========================================================================
    // Pending Sync Operations
    // ==========================================================================

    getPendingSyncCount(): Observable<{ count: number; batch_count: number }> {
        return this.http.get<{ count: number; batch_count: number }>(`${this.apiUrl}/sync/pending/count`);
    }

    getPendingBatches(): Observable<PendingBatchListResponse> {
        return this.http.get<PendingBatchListResponse>(`${this.apiUrl}/sync/pending`);
    }

    approveSyncChanges(batchId: number, changeIds: number[]): Observable<SyncApproveResponse> {
        return this.http.post<SyncApproveResponse>(`${this.apiUrl}/sync/approve`, {
            batch_id: batchId,
            change_ids: changeIds,
            action: 'approve'
        });
    }

    rejectSyncChanges(batchId: number, changeIds: number[]): Observable<SyncApproveResponse> {
        return this.http.post<SyncApproveResponse>(`${this.apiUrl}/sync/approve`, {
            batch_id: batchId,
            change_ids: changeIds,
            action: 'reject'
        });
    }

    // ==========================================================================
    // Change Logs
    // ==========================================================================

    getChangeLogs(params: { entity_type?: string; entity_id?: number; source?: string; limit?: number; offset?: number } = {}): Observable<ChangeLogResponse> {
        return this.http.get<ChangeLogResponse>(`${this.apiUrl}/change-logs`, { params: params as any });
    }
}

// ==========================================================================
// Additional Interfaces
// ==========================================================================

export interface PendingChangeInfo {
    id: number;
    entity_id: number;
    entity_name: string | null;
    entity_sku: string | null;
    field: string;
    old_value: string | null;
    new_value: string | null;
    status: string;
}

export interface PendingBatchInfo {
    id: number;
    source: string;
    status: string;
    total_changes: number;
    approved_count: number;
    rejected_count: number;
    created_at: string;
    changes: PendingChangeInfo[];
}

export interface PendingBatchListResponse {
    batches: PendingBatchInfo[];
    total_pending: number;
}

export interface SyncApproveResponse {
    success: boolean;
    applied_count: number;
    message: string;
    errors: string[];
}

export interface ChangeLogEntry {
    id: number;
    entity_type: string;
    entity_id: number;
    entity_name: string | null;
    field: string;
    old_value: string | null;
    new_value: string | null;
    source: string;
    changed_by_email: string | null;
    changed_at: string;
}

export interface ChangeLogResponse {
    entries: ChangeLogEntry[];
    total: number;
}
