export interface ProductImage {
  id: number;
  product_id: number;
  image_path: string;
  is_primary: number;
  source?: string;
  title?: string;
  description?: string;
}

export interface InventoryItem {
  id: number;
  product_id: number;
  quantity: number;
  location?: string;
}

export interface InventoryAdjustment {
  id: number;
  product_id: number;
  adjustment: number;
  reason: string | null;
  timestamp: string;
  created_by: string | null;
}

export interface ProductCustomField {
  id: number;
  product_id: number;
  custom_field_id: number;
  value: string;
}

export interface ProductVariant {
  id: number;
  product_id: number;
  name: string;
  sku: string;
  price: number;
  stock_quantity: number;
  attributes: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface Product {
  id: number;
  name: string;
  description: string;
  sku: string;
  supplier_id?: number;
  default_resale_price: number;
  cost_price?: number;
  properties?: any;
  images?: ProductImage[];
  inventory_items?: InventoryItem[];
  inventory_adjustments?: InventoryAdjustment[];
  manufacturer?: string;
  brand?: string;
  category?: string;
  width?: number;
  height?: number;
  depth?: number;
  weight?: number;
  primary_image?: ProductImage;
  custom_fields?: ProductCustomField[];
  variants?: ProductVariant[];
}