export interface SupplierProductAlias {
    id: number;
    supplier_id: number;
    product_id: number;
    variant_id?: number | null;
    alias_sku?: string | null;
    alias_name?: string | null;
    normalized_sku?: string | null;
    normalized_name?: string | null;
    source: string;
    confidence: number;
    match_count: number;
    is_active: boolean;
    last_matched_at?: string | null;
    created_at: string;
    updated_at: string;
    product_name?: string | null;
    variant_name?: string | null;
}

export interface SupplierProduct {
    id: number;
    product_id: number;
    supplier_id: number;
    supplier_sku?: string;
    supplier_product_name?: string;
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
    aliases?: SupplierProductAlias[];
}
