export enum PurchaseOrderStatus {
    DRAFT = 'draft',
    ORDERED = 'ordered',
    PARTIALLY_RECEIVED = 'partially_received',
    COMPLETED = 'completed',
    CLOSED = 'closed'
}

export interface PurchaseOrderItem {
    id?: number;
    product_id: number;
    variant_id?: number;
    product_name?: string; // Enriched in frontend if needed
    product?: {
        id: number;
        name: string;
        sku: string;
        images?: any[];
        variants?: any[];
    };
    variant?: {
        id: number;
        name: string;
        sku: string;
    };
    quantity_ordered: number;
    quantity_received?: number;
    unit_cost: number;
    supplier_sku?: string;
    supplier_product_name?: string;
}

export interface PurchaseOrder {
    id: number;
    supplier_id: number;
    supplier_name?: string; // Enriched
    status: PurchaseOrderStatus;

    total_amount: number;
    currency: string;
    exchange_rate: number;

    landed_cost?: number;
    shipping_cost?: number;
    tax_amount?: number;
    other_costs?: number;

    notes?: string;
    created_at: string;
    updated_at?: string;
    items: PurchaseOrderItem[];

    // Payment Info
    payment_status?: string;
    payment_method?: string;
    custom_payer_name?: string;
    paid_by_user_id?: number;
    ordered_at?: string;
    received_at?: string;
}

export interface PurchaseOrderCreate {
    supplier_id: number;
    status?: PurchaseOrderStatus;
    currency?: string;
    exchange_rate?: number;
    notes?: string;
    shipping_cost?: number;
    tax_amount?: number;
    other_costs?: number;
    items: Partial<PurchaseOrderItem>[];
    payment_status?: string;
    payment_method?: string;
    custom_payer_name?: string;
    paid_by_user_id?: number;
    ordered_at?: string;
    received_at?: string;
}
