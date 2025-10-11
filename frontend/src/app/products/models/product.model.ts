export interface ProductImage {
  id: number;
  product_id: number;
  image_path: string;
  is_primary: number;
  source?: string;
}

export interface InventoryItem {
  id: number;
  product_id: number;
  quantity: number;
  location?: string;
}

export interface ProductCustomField {
  id: number;
  product_id: number;
  custom_field_id: number;
  value: string;
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
  manufacturer?: string;
  brand?: string;
  category?: string;
  width?: number;
  height?: number;
  depth?: number;
  weight?: number;
  primary_image?: ProductImage;
  inventory_items?: InventoryItem[];
  custom_fields?: ProductCustomField[];
}