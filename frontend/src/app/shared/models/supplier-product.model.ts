export interface SupplierProduct {
    id: number;
    product_id: number;
    supplier_id: number;
    supplier_sku?: string;
    cost_price: number;
    is_primary: boolean;
    lead_time_days?: number;
    minimum_order_qty: number;
    notes?: string;
    last_ordered_at?: string;
    created_at: string;
    updated_at: string;
    product_name?: string;
    supplier_name?: string;
}
